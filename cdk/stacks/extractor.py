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
    aws_lambda as lambda_
)

ROOT_DIR = path.join(path.dirname(__file__),'..')

class MovementExtractorConstruct(Construct, IQueuedTask):
  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure) -> None:
    super().__init__(scope, id)

    self.function = lambda_.DockerImageFunction(self,'Function',
      allow_all_outbound=True,
      architecture= lambda_.Architecture.X86_64,
      dead_letter_queue= sqs.Queue(self,'DLQ',
        queue_name='MovementExtractor_Function_dlq',
        retention_period= cdk.Duration.days(14)),
      environment={
        #'AWS_REGION': cdk.Aws.REGION,
        'DATA_BUCKET': infra.storage.data_bucket.bucket_name
      },
      function_name='MovementExtractor_S3Batch',
      log_retention= logs.RetentionDays.TWO_WEEKS,
      memory_size=256,
      tracing=lambda_.Tracing.ACTIVE,
      timeout=cdk.Duration.minutes(1),
      vpc= infra.network.vpc,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name='Default'),
      code = lambda_.DockerImageCode.from_image_asset(
        directory= path.join(ROOT_DIR,'src/eval')))
      
    infra.storage.data_bucket.grant_read_write(self.function.role)
    self.function.role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name('AWSXrayWriteOnlyAccess'))