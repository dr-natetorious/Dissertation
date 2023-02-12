import builtins
from stacks.interfaces import IBaseInfrastructure, IDataCollection, IQueuedTask
from os import path
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import(
    aws_ec2 as ec2,
    aws_autoscaling as asg,
    aws_s3 as s3,
    aws_iam as iam,
    aws_sqs as sqs,
    aws_ecs as ecs,
    aws_logs as logs,
    aws_dynamodb as ddb,
    aws_ecs_patterns as ecs_p,
)

ROOT_DIR = path.join(path.dirname(__file__),'..')

def create_user_data():
  return '\n'.join([
    "#!/bin/bash",
    "echo ECS_ENABLE_GPU_SUPPORT=true >> /etc/ecs/ecs.config"
  ])

class OpenPoseGpuConstruct(Construct, IQueuedTask):

  @property
  def task_queue(self)->sqs.IQueue:
    return self.__task_queue

  @task_queue.setter
  def task_queue(self,value)->None:
    self.__task_queue = value

  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure) -> None:
    super().__init__(scope, id)
    cdk.Tags.of(self).add(key='construct', value=OpenPoseGpuConstruct.__name__)

    self.task_queue = sqs.Queue(self,'TaskQueue',
      queue_name='openpose-tasks_gpu',
      retention_period=cdk.Duration.days(14),
      dead_letter_queue=sqs.DeadLetterQueue(
        max_receive_count=1,
        queue= sqs.Queue(self,'DLQ',
          retention_period=cdk.Duration.days(14))
        )
      )
      
    status_table = ddb.Table(self,'StatusTable',
      table_name='openpose-status_gpu',
      billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
      point_in_time_recovery=True,
      table_class= ddb.TableClass.STANDARD,
      partition_key= ddb.Attribute(name='VideoId',type=ddb.AttributeType.STRING),
      sort_key= ddb.Attribute(name='SortKey', type=ddb.AttributeType.STRING),
      time_to_live_attribute='Expiration')


    log_group = logs.LogGroup(self,'LogGroup',
      retention= logs.RetentionDays.TWO_WEEKS)

    task_definition= ecs.Ec2TaskDefinition(
      self,'Definition',
      family= 'LINUX',
      network_mode= ecs.NetworkMode.AWS_VPC
    )

    task_definition.add_container('OpenPoseGpu',
      memory_limit_mib=3*1024,
      gpu_count=1,
      image=ecs.ContainerImage.from_asset(path.join(ROOT_DIR,'src','analyze')),
      container_name='openpose-analyzer',
      port_mappings=[
        ecs.PortMapping(
          name='health_check',
          container_port=80,
          host_port=80,
          protocol= ecs.Protocol.TCP)
      ],
      logging= ecs.LogDrivers.aws_logs(
        log_group= log_group,
        stream_prefix='analyzer'
      ),
      essential=False,
      environment={
        'AWS_REGION': cdk.Aws.REGION,
        'TASK_QUEUE_URL': self.task_queue.queue_url,
        'STATUS_TABLE': status_table.table_name,
        'DATA_BUCKET': infra.storage.data_bucket.bucket_name,
        'AWS_XRAY_DAEMON_ADDRESS': '0.0.0.0:2000',
      })

    task_definition.add_container('XRay',
      memory_reservation_mib=256,
      image= ecs.ContainerImage.from_registry(name='amazon/aws-xray-daemon'),
      container_name='xray-sidecar',
      essential=True,
      logging= ecs.LogDrivers.aws_logs(
        log_group=log_group,
        stream_prefix='xray-sidecar'
      ),
      port_mappings=[
        ecs.PortMapping(
          name='xray_sidecar',
          host_port=2000,
          container_port=2000,
          protocol=ecs.Protocol.UDP)
      ],
      environment={
        'AWS_REGION': cdk.Aws.REGION
      })


    cluster = ecs.Cluster(self,'GpuCluster',
      cluster_name='openpose_gpu',
      vpc= infra.network.vpc,
      # capacity= ecs.AddCapacityOptions(
      #   machine_image_type= ecs.MachineImageType.AMAZON_LINUX_2,
      #   machine_image= ecs.EcsOptimizedImage.amazon_linux2(hardware_type= ecs.AmiHardwareType.GPU),
      #   allow_all_outbound=True,
      #   cooldown= cdk.Duration.minus(15),
      #   desired_capacity=1,
      #   spot_price='50',
      #   vpc_subnets= ec2.SubnetSelection(subnet_group_name='Default'),
      #   instance_type= ec2.InstanceType.of(ec2.InstanceClass.G4DN, instance_size=ec2.InstanceSize.XLARGE),
      # )
    )

    ecs.Ec2Service(self,'Service',
      task_definition= task_definition,
      assign_public_ip=False,
      cluster= cluster,
      desired_count=1,
      # placement_constraints=[
      #   ecs.PlacementConstraint.member_of("attribute:ec2.instance-type==g4dn.xlarge")
      # ],
      vpc_subnets= ec2.SubnetSelection(subnet_group_name='Default'))

    scale_group = asg.AutoScalingGroup(self,'Asg',
      auto_scaling_group_name='asg-analyze-video-gpu',
      vpc= infra.network.vpc,
      launch_template= ec2.LaunchTemplate(self,'OpenPoseHostLaunchTemplate',
        detailed_monitoring=True,
        #launch_template_name='openpose_gpu',
        security_group= infra.network.open_security_group,
        key_name='us-east-2.dissertation.natetorio.us',
        user_data=ec2.UserData.for_linux(shebang=create_user_data()),
        role= iam.Role(self,'AsgRole',
          assumed_by=iam.ServicePrincipal(service='ec2'),
          managed_policies=[
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSQSFullAccess'),
            iam.ManagedPolicy.from_aws_managed_policy_name('AWSXrayWriteOnlyAccess'),
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'),
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess'),
            iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AmazonEC2RoleforSSM'),
        ]),
        spot_options= ec2.LaunchTemplateSpotOptions(
          max_price=50,
          request_type= ec2.SpotRequestType.ONE_TIME,          
        ),
        instance_type= ec2.InstanceType.of(ec2.InstanceClass.G4DN, instance_size=ec2.InstanceSize.XLARGE),
        machine_image= ecs.EcsOptimizedImage.amazon_linux2(hardware_type= ecs.AmiHardwareType.GPU)),
      allow_all_outbound=True,
      max_capacity=1,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name='Default'),
    )

    scale_group.scale_on_metric('QueueDepth',
      metric = self.task_queue.metric_approximate_number_of_messages_visible(
        period= cdk.Duration.minutes(15),
      ),
      adjustment_type= asg.AdjustmentType.CHANGE_IN_CAPACITY,
      estimated_instance_warmup= cdk.Duration.minutes(1),
      scaling_steps=[
        asg.ScalingInterval(change=1,lower=1000),
        asg.ScalingInterval(change=2,lower=2000),
      ])

    cluster.add_asg_capacity_provider(
      provider = ecs.AsgCapacityProvider(self,'AsgProvider',
        auto_scaling_group= scale_group,
        enable_managed_scaling=True))

    self.task_queue.grant_consume_messages(task_definition.task_role)
    status_table.grant_read_write_data(task_definition.task_role)
    infra.storage.data_bucket.grant_read_write(task_definition.task_role)
    task_definition.task_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsFullAccess'))
    task_definition.task_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSXrayWriteOnlyAccess'))
