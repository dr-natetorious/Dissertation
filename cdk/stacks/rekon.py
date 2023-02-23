import builtins
from stacks.interfaces import IBaseInfrastructure
from shared.monitor_s3jobs import MonitorS3BatchJobConstruct
from os import path
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import(
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_logs as logs,
    aws_sqs as sqs,
    aws_lambda as lambda_,
    aws_dynamodb as ddb,
)

ROOT_DIR = path.join(path.dirname(__file__),'..')

class RekognitionConstruct(Construct):

  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure) -> None:
    super().__init__(scope, id)    

    self.bucket = s3.Bucket(self,'Bucket',
      bucket_name='rekognition.us-east-2.dissertation.natetorio.us')

    status_table = ddb.Table(self,'StatusTable',
      table_name='rekon-status-table',
      billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
      point_in_time_recovery=True,
      table_class= ddb.TableClass.STANDARD,
      partition_key= ddb.Attribute(name='VideoId',type=ddb.AttributeType.STRING),
      sort_key= ddb.Attribute(name='SortKey', type=ddb.AttributeType.STRING),
      time_to_live_attribute='Expiration')

    self.function = lambda_.DockerImageFunction(self,'Function',
      allow_all_outbound=True,
      log_retention= logs.RetentionDays.TWO_WEEKS,
      architecture= lambda_.Architecture.X86_64,
      dead_letter_queue= sqs.Queue(self,'DLQ',
        queue_name='Rekognition_S3Batch_dlq',
        retention_period= cdk.Duration.days(14)),
      environment={
        'DATA_BUCKET': infra.storage.data_bucket.bucket_name,
        'STATUS_TABLE': status_table.table_name,
      },
      function_name='Rekognition_S3Batch',
      memory_size=256,
      tracing=lambda_.Tracing.ACTIVE,
      timeout=cdk.Duration.minutes(5),
      vpc= infra.network.vpc,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name='Default'),
      code = lambda_.DockerImageCode.from_image_asset(
        directory= path.join(ROOT_DIR,'src/rekon')))

    self.monitor = MonitorS3BatchJobConstruct(self,'Monitor',
      infra=infra,
      trigger_bucket= self.bucket,
      handler = self.function)

    status_table.grant_read_write_data(self.function.role)
    infra.storage.data_bucket.grant_read_write(self.function.role)
    self.function.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSXrayWriteOnlyAccess'))
