import builtins
from stacks.interfaces import IBaseInfrastructure, IDataCollection, IQueuedTask
from stacks.analyze_video_gpu import OpenPoseGpuConstruct
from os import path
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import(
    aws_s3 as s3,
    aws_lambda_event_sources as les,
    aws_iam as iam,
    aws_lambda as lambda_,
)

ROOT_DIR = path.join(path.dirname(__file__),'..')

class MonitorS3BatchJobConstruct(Construct):
  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure,
               trigger_bucket:s3.IBucket,
               handler:lambda_.IFunction,
               manifest_prefix:str='manifest',
               manifest_suffix:str='.csv') -> None:
    super().__init__(scope, id)

    self.batch_role = iam.Role(self,'BatchRole',
      assumed_by=iam.ServicePrincipal('batchoperations.s3.amazonaws.com'))
    
    infra.storage.data_bucket.grant_read_write(self.batch_role)
    trigger_bucket.grant_read(self.batch_role)
    handler.grant_invoke(self.batch_role)

    with open(path.join(ROOT_DIR,'src','start-manifest','index.py'), 'rt') as f:
      code = lambda_.Code.from_inline(f.read())

    forward_function = lambda_.Function(self,'Function',
      code= code,
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
      bucket=trigger_bucket,
      events=[s3.EventType.OBJECT_CREATED],
      filters=[
        s3.NotificationKeyFilter(
          prefix=manifest_prefix,
          suffix=manifest_suffix)
      ]
    ))