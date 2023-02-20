import builtins
from stacks.interfaces import IBaseInfrastructure, IDataCollection, IQueuedTask
from stacks.analyze_video_gpu import OpenPoseGpuConstruct
from os import path
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import(
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_iam as iam,
    aws_sqs as sqs,
    aws_ecs as ecs,
    aws_logs as logs,
    aws_dynamodb as ddb,
    aws_lambda as lambda_,
    aws_kinesis as kinesis,
    aws_kinesisfirehose as hose,
)

ROOT_DIR = path.join(path.dirname(__file__),'..')

class SkeletalStream(Construct):
  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure) -> None:
    super().__init__(scope, id)

    firehose_role = iam.Role(self,'FirehoseRole',
      assumed_by= iam.ServicePrincipal('firehose'))

    self.metadata_stream = kinesis.Stream(self,'Stream',
      stream_name= 'skeleton-metadata',
      retention_period= cdk.Duration.days(90),
      shard_count=3)
    
    log_group = logs.LogGroup(self,'DeliveryLogs',
      removal_policy= cdk.RemovalPolicy.DESTROY,
      retention= logs.RetentionDays.FIVE_DAYS)
        
    self.firehose = hose.CfnDeliveryStream(self,'Firehose',
      delivery_stream_name='skeleton-delivery',
      kinesis_stream_source_configuration= hose.CfnDeliveryStream.KinesisStreamSourceConfigurationProperty(
        kinesis_stream_arn= self.metadata_stream.stream_arn,
        role_arn= firehose_role.role_arn
      ),
      extended_s3_destination_configuration= hose.CfnDeliveryStream.ExtendedS3DestinationConfigurationProperty(
        compression_format= 'GZIP',
        prefix='movement-extraction/metadata/',
        role_arn= firehose_role.role_arn,
        error_output_prefix='error/movement-extraction/metadata/',
        cloud_watch_logging_options= hose.CfnDeliveryStream.CloudWatchLoggingOptionsProperty(
          enabled=True,
          log_group_name= log_group.log_group_name,
          log_stream_name= 'SkeletalStreamFirehose'
        ),
        bucket_arn= infra.storage.movement_bucket.bucket_arn,
        buffering_hints= hose.CfnDeliveryStream.BufferingHintsProperty(
          interval_in_seconds=60,
          size_in_m_bs=128
        )
    ))

    log_group.grant_write(firehose_role)
    self.metadata_stream.grant_read(firehose_role)
    infra.storage.movement_bucket.grant_write(firehose_role)

class MovementExtractorConstruct(Construct, IQueuedTask):
  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure) -> None:
    super().__init__(scope, id)

    self.output_stream = SkeletalStream(self,'Output', infra=infra)    
    self.function = lambda_.DockerImageFunction(self,'Function',
      allow_all_outbound=True,
      architecture= lambda_.Architecture.X86_64,
      dead_letter_queue= sqs.Queue(self,'DLQ',
        queue_name='MovementExtractor_Function_dlq',
        retention_period= cdk.Duration.days(14)),
      environment={
        #'AWS_REGION': cdk.Aws.REGION,
        'METADATA_STREAM': self.output_stream.metadata_stream.stream_name,
        'DATA_BUCKET': infra.storage.data_bucket.bucket_name
      },
      function_name='MovementExtractor_S3Batch',
      log_retention= logs.RetentionDays.TWO_WEEKS,
      memory_size=1024,
      tracing=lambda_.Tracing.ACTIVE,
      timeout=cdk.Duration.minutes(5),
      vpc= infra.network.vpc,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name='Default'),
      code = lambda_.DockerImageCode.from_image_asset(
        directory= path.join(ROOT_DIR,'src/extract')))
      
    self.batch_role = iam.Role(self,'BatchRole',
      role_name='Extract_BatchRole',
      assumed_by=iam.ServicePrincipal('batchoperations.s3.amazonaws.com'))
    
    infra.storage.data_bucket.grant_read_write(self.batch_role)
    self.function.grant_invoke(self.batch_role)
    self.output_stream.metadata_stream.grant_write(self.function.role)
    infra.storage.data_bucket.grant_read_write(self.function.role)
    self.function.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSXrayWriteOnlyAccess'))