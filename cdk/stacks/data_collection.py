import builtins
from stacks.interfaces import IBaseInfrastructure, IDataCollection, IQueuedTask
from os import path
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import(
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_logs as logs,
    aws_sqs as sqs,
    aws_ecs as ecs,
    aws_dynamodb as ddb,
)

ROOT_DIR = path.join(path.dirname(__file__),'..')

class YouTubeDownloadConstruct(Construct, IQueuedTask):

  @property
  def task_queue(self)->sqs.IQueue:
    return self.__task_queue

  @task_queue.setter
  def task_queue(self,value)->None:
    self.__task_queue = value

  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure) -> None:
    super().__init__(scope, id)

    self.task_queue_dlq = sqs.Queue(self,'DLQ',
      queue_name='youtube-download-tasks_dlq',
      retention_period=cdk.Duration.days(14))

    self.task_queue = sqs.Queue(self,'TaskQueue',
      queue_name='youtube-download-tasks',
      retention_period=cdk.Duration.days(14),
      dead_letter_queue=sqs.DeadLetterQueue(
        max_receive_count=2,
        queue= self.task_queue_dlq))

    status_table = ddb.Table(self,'StatusTable',
      billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
      point_in_time_recovery=True,
      table_class= ddb.TableClass.STANDARD,
      partition_key= ddb.Attribute(name='VideoId',type=ddb.AttributeType.STRING),
      sort_key= ddb.Attribute(name='SortKey', type=ddb.AttributeType.STRING),
      time_to_live_attribute='Expiration')


    log_group = logs.LogGroup(self,'LogGroup',
      retention= logs.RetentionDays.TWO_WEEKS)
      #log_group_name='/natetorious/kinetic/youtube')

    task_definition= ecs.FargateTaskDefinition(
      self,'Definition',
      cpu=2048,
      memory_limit_mib=4096,
      runtime_platform= ecs.RuntimePlatform(
        cpu_architecture= ecs.CpuArchitecture.X86_64,
        operating_system_family= ecs.OperatingSystemFamily.LINUX),
    )

    task_definition.add_container('Collector', 
      image=ecs.ContainerImage.from_asset(path.join(ROOT_DIR,'src','pipeline/collection')),
      container_name='youtube-download',
      port_mappings=[
        ecs.PortMapping(
          name='health_check',
          container_port=80,
          host_port=80,
          protocol= ecs.Protocol.TCP)
      ],
      logging= ecs.LogDrivers.aws_logs(
        log_group= log_group,
        stream_prefix='collector'
      ),
      essential=True,
      environment={
        'AWS_REGION': cdk.Aws.REGION,
        'TASK_QUEUE_URL': self.task_queue.queue_url,
        #'TASK_QUEUE_URL':'https://sqs.us-east-2.amazonaws.com/995765563608/youtube-download-tasks_dlq',
        'STATUS_TABLE': status_table.table_name,
        'DATA_BUCKET': infra.storage.data_bucket.bucket_name,
        'AWS_XRAY_DAEMON_ADDRESS': '0.0.0.0:2000',
      })

    task_definition.add_container('XRay',
      image= ecs.ContainerImage.from_registry(name='amazon/aws-xray-daemon'),
      container_name='xray-sidecar',
      #memory_limit_mib=128,
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

    service = ecs.FargateService(self,'Service',
      service_name='youtube-collector',
      task_definition= task_definition,
      assign_public_ip=False,      
      platform_version= ecs.FargatePlatformVersion.LATEST,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name='Default'),
      cluster = infra.compute.fargate_cluster,
      desired_count=0,
      capacity_provider_strategies=[
        ecs.CapacityProviderStrategy(capacity_provider='FARGATE_SPOT', weight=2),
        ecs.CapacityProviderStrategy(capacity_provider='FARGATE', weight=1)
      ])

    for queue in [self.task_queue, self.task_queue_dlq]:
      queue.grant_consume_messages(service.task_definition.task_role)

    status_table.grant_read_write_data(service.task_definition.task_role)
    infra.storage.data_bucket.grant_read_write(service.task_definition.task_role)
    task_definition.task_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSXrayWriteOnlyAccess'))

class DataCollectionConstruct(Construct):
  def __init__(self, scope:Construct, id:str, infra:IBaseInfrastructure,**kwargs)->None:
    super().__init__(scope,id,**kwargs)
    
    self.youtube = YouTubeDownloadConstruct(self,'YouTube',infra=infra)
    return