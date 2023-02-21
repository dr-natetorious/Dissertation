import builtins
from stacks.interfaces import IBaseInfrastructure, IDataCollection, IQueuedTask
from stacks.analyze_video_gpu import OpenPoseGpuConstruct
from os import path
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import(
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_lambda_event_sources as les,
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

class ManifestMonitor(Construct):
  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure, handler:lambda_.IFunction) -> None:
    super().__init__(scope, id)

    self.bucket = s3.Bucket(self,'Bucket',
      bucket_name='manifest.us-east-2.dissertation.natetorio.us')

    self.batch_role = iam.Role(self,'BatchRole',
      role_name='Extract_BatchRole',
      assumed_by=iam.ServicePrincipal('batchoperations.s3.amazonaws.com'))
    
    infra.storage.data_bucket.grant_read_write(self.batch_role)
    self.bucket.grant_read(self.batch_role)
    handler.grant_invoke(self.batch_role)

    with open(path.join(ROOT_DIR,'src','start-manifest','index.py'), 'rt') as f:
      code = lambda_.Code.from_inline(f.read())

    forward_function = lambda_.Function(self,'Function',
      code= code,
      function_name='StartManifestFile',
      handler='index.lambda_function',
      runtime= lambda_.Runtime.PYTHON_3_8,
      tracing= lambda_.Tracing.ACTIVE,
      timeout= cdk.Duration.seconds(30),
      environment={
        'ACCOUNT_ID': cdk.Aws.ACCOUNT_ID,
        'FUNCTION_ARN': handler.function_arn,
        'REPORT_BUCKET_ARN': infra.storage.data_bucket.bucket_arn,
        'BATCH_ROLE_ARN': self.batch_role.role_arn,    
      },
    )
        
    forward_function.role.attach_inline_policy(iam.Policy(self,'CreateJobPolicy',
      document=iam.PolicyDocument(
        statements=[
          iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
              's3:CreateJob'
            ],
            resources=['*']),
          iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
              'iam:PassRole',
              'iam:GetRole'
            ],
            resources=[self.batch_role.role_arn]),
        ]
      )))

    forward_function.add_event_source(les.S3EventSource(
      bucket=self.bucket,
      events=[s3.EventType.OBJECT_CREATED],
      filters=[
        s3.NotificationKeyFilter(
            prefix="manifest",
            suffix=".csv")
      ]
    ))

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

class MissingReportHandlerConstruct(Construct):
  def __init__(self, scope: Construct, id: builtins.str) -> None:
    super().__init__(scope, id)

    self.fetch_queue = sqs.Queue(self,'FetchQueue',
      queue_name='MovementExtractor-FetchQueue',
      retention_period=cdk.Duration.days(14))

class MovementExtractorConstruct(Construct, IQueuedTask):
  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure) -> None:
    super().__init__(scope, id)

    self.output_stream = SkeletalStream(self,'Output', infra=infra)
    self.missing_reports_handler = MissingReportHandlerConstruct(self,'MissingReports')

    status_table = ddb.Table(self,'StatusTable',
      table_name='MovementExtractor_status-table',
      billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
      point_in_time_recovery=True,
      table_class= ddb.TableClass.STANDARD,
      partition_key= ddb.Attribute(name='VideoId',type=ddb.AttributeType.STRING),
      sort_key= ddb.Attribute(name='SortKey', type=ddb.AttributeType.STRING),
      time_to_live_attribute='Expiration')
        
    self.function = lambda_.DockerImageFunction(self,'Function',
      allow_all_outbound=True,
      architecture= lambda_.Architecture.X86_64,
      dead_letter_queue= sqs.Queue(self,'DLQ',
        queue_name='MovementExtractor_Function_dlq',
        retention_period= cdk.Duration.days(14)),
      environment={
        'FETCH_QUEUE': self.missing_reports_handler.fetch_queue.queue_url,
        'METADATA_STREAM': self.output_stream.metadata_stream.stream_name,
        'DATA_BUCKET': infra.storage.data_bucket.bucket_name,
        'STATUS_TABLE': status_table.table_name,
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
    
    self.input_monitor = ManifestMonitor(self,'InputMonitor',
      infra=infra,
      handler=self.function)

    self.missing_reports_handler.fetch_queue.grant_send_messages(self.function.role)
    status_table.grant_read_write_data(self.function.role)
    self.output_stream.metadata_stream.grant_write(self.function.role)
    infra.storage.data_bucket.grant_read_write(self.function.role)
    self.function.role.add_managed_policy(
      iam.ManagedPolicy.from_aws_managed_policy_name('AWSXrayWriteOnlyAccess'))