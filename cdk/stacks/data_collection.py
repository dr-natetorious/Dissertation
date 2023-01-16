import builtins
from stacks.interfaces import IBaseInfrastructure, IDataCollection, IQueuedTask
from os import path
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import(
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_sqs as sqs,
    aws_ecs as ecs,
    aws_dynamodb as ddb,
    aws_ecs_patterns as ecs_p,
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

    self.task_queue = sqs.Queue(self,'TaskQueue')
    status_table = ddb.Table(self,'StatusTable',
      billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
      point_in_time_recovery=True,
      table_class= ddb.TableClass.STANDARD,
      partition_key= ddb.Attribute(name='VideoId',type=ddb.AttributeType.STRING),
      sort_key= ddb.Attribute(name='SortKey', type=ddb.AttributeType.STRING),
      time_to_live_attribute='Expiration')

    service = ecs_p.QueueProcessingFargateService(self,'Service',
      queue = self.task_queue,
      memory_limit_mib=1024,
      cpu=512,
      max_scaling_capacity=0,
      min_scaling_capacity=0,
      vpc= infra.network.vpc,
      image=ecs.ContainerImage.from_asset(path.join(ROOT_DIR,'src','collection')),
      platform_version= ecs.FargatePlatformVersion.LATEST,
      task_subnets= ec2.SubnetSelection(subnet_group_name='Default'),
      environment={
        'TASK_QUEUE_URL': self.task_queue.queue_url,
        'STATUS_TABLE': status_table.table_name,
        'DATA_BUCKET': infra.storage.data_bucket.bucket_name,
      },
      capacity_provider_strategies=[
        ecs.CapacityProviderStrategy(capacity_provider='FARGATE_SPOT', weight=2),
        ecs.CapacityProviderStrategy(capacity_provider='FARGATE', weight=1)
      ])

    self.task_queue.grant_consume_messages(service.task_definition.execution_role)
    status_table.grant_read_write_data(service.task_definition.execution_role)

class DataCollectionConstruct(Construct):
  def __init__(self, scope:Construct, id:str, infra:IBaseInfrastructure,**kwargs)->None:
    super().__init__(scope,id,**kwargs)
    
    self.youtube = YouTubeDownloadConstruct(self,'YouTube',infra=infra)
    return