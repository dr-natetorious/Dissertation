import builtins
from stacks.interfaces import IBaseInfrastructure, IQueuedTask
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
    aws_lambda as lambda_,
    aws_ecs_patterns as ecs_p,
    aws_apigateway as api,
)

ROOT_DIR = path.join(path.dirname(__file__),'..')

class DataApiConstruct(Construct):
  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure) -> None:
    super().__init__(scope, id)
    cdk.Tags.of(self).add(key='construct', value=DataApiConstruct.__name__)

    function = lambda_.DockerImageFunction(self,'Function',
      function_name='DataApi-Handler',
      environment={
      
      },
      vpc= infra.network.vpc,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name='Default'),
      memory_size=256,
      tracing= lambda_.Tracing.ACTIVE,
      code = lambda_.DockerImageCode.from_image_asset(
        directory= path.join(ROOT_DIR,'src/api')))
    
    gateway = api.LambdaRestApi(self,'Gateway',
      handler= function,
      proxy=True,
      description='Data API for interacting with Kinetic',
      cloud_watch_role=True)