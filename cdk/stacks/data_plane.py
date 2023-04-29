import builtins
from os import path
import aws_cdk as cdk
from json import dumps
from stacks.interfaces import IBaseInfrastructure
from constructs import Construct
from aws_cdk import(
    aws_lambda as lambda_,
    aws_ec2 as ec2,
    aws_appsync as appsync,
    aws_logs as logs,
    aws_sns as sns,
    aws_logs as logs,
    aws_dynamodb as ddb,
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as e_targets,
)

ROOT_DIR = path.join(path.dirname(__file__),'..')

class AnnotationDataSource(Construct):
  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure, graphql:appsync.IGraphqlApi) -> None:
    super().__init__(scope, id)

    self.annotation_table = ddb.Table(self,'Table',
      table_name='video-annotations',
      billing_mode= ddb.BillingMode.PAY_PER_REQUEST,
      removal_policy = cdk.RemovalPolicy.DESTROY,
      partition_key= ddb.Attribute(name='VideoId', type=ddb.AttributeType.STRING))

    function = lambda_.Function(self,'Function',
      function_name='kinetic-graphql-annotations',
      code=lambda_.Code.from_asset(path.join(ROOT_DIR,'src/data/get-annotations')),
      handler='index.lambda_function',
      log_retention= logs.RetentionDays.FIVE_DAYS,
      architecture= lambda_.Architecture.ARM_64,
      runtime= lambda_.Runtime.PYTHON_3_9,
      vpc= infra.network.vpc,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name='Default'),
      environment={
        'TABLE_NAME': self.annotation_table.table_name,
        'REGION': cdk.Aws.REGION,
      })
    
    self.annotation_table.grant_read_data(function)
    
    lambda_source = graphql.add_lambda_data_source('AnnotationLambdaSource',
      name='AnnotationQuerySource',
      lambda_function=function)
    
    graphql.create_resolver('GetAnnotation',
      type_name='Query',
      field_name='get_annotation',
      data_source=lambda_source,
      request_mapping_template=appsync.MappingTemplate.lambda_request(),
      response_mapping_template=appsync.MappingTemplate.lambda_result())

    graphql.create_resolver('GetVideoAnnotation',
      type_name='Video',
      field_name='annotation',
      data_source=lambda_source,
      request_mapping_template=appsync.MappingTemplate.lambda_request(),
      response_mapping_template=appsync.MappingTemplate.lambda_result())

class KineticLambdaDataSource(Construct):
  @property
  def function_name(self)->str:
    return 'kinetic-graphql-'+self.__class__.__name__

  @property
  def code(self)->lambda_.Code:
    raise NotImplementedError()

  @property
  def type_name(self)->str:
    raise NotImplementedError()
  
  @property
  def field_name(self)->str:
    raise NotImplementedError()

  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure, graphql:appsync.IGraphqlApi, environment=None) -> None:
    super().__init__(scope, id)

    if environment is None:
      environment = dict()

    environment.update({
      'BUCKET': infra.storage.data_bucket.bucket_name,
      'REGION': cdk.Aws.REGION
    })

    self.function = lambda_.Function(self,'Function',
      function_name=self.function_name,
      code=self.code,
      handler='index.lambda_function', 
      architecture= lambda_.Architecture.ARM_64,
      runtime= lambda_.Runtime.PYTHON_3_9,
      log_retention= logs.RetentionDays.FIVE_DAYS,
      vpc= infra.network.vpc,
      vpc_subnets= ec2.SubnetSelection(subnet_group_name='Default'),
      environment=environment)
    
    infra.storage.data_bucket.grant_read(self.function)

    lambda_source = graphql.add_lambda_data_source(self.__class__.__name__,
      lambda_function=self.function)

    graphql.create_resolver('%s/%s'%(self.type_name,self.field_name),
      type_name=self.type_name,
      field_name=self.field_name,
      data_source=lambda_source,
      request_mapping_template=appsync.MappingTemplate.lambda_request(),
      response_mapping_template=appsync.MappingTemplate.lambda_result())

class VideoDataSource(KineticLambdaDataSource):
  @property
  def code(self)->lambda_.Code:
    return lambda_.Code.from_asset(path.join(ROOT_DIR,'src/data/get-video'))

  @property
  def type_name(self)->str:
    return 'Query'
  
  @property
  def field_name(self)->str:
    return 'get_video'

  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure, graphql:appsync.IGraphqlApi) -> None:
    super().__init__(scope, id, infra, graphql)

class PeopleDataSource(KineticLambdaDataSource):
  @property
  def code(self)->lambda_.Code:
    return lambda_.Code.from_asset(path.join(ROOT_DIR,'src/data/get-person'))

  @property
  def type_name(self)->str:
    return 'Video'
  
  @property
  def field_name(self)->str:
    return 'people'

  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure, graphql:appsync.IGraphqlApi) -> None:
    super().__init__(scope, id, infra, graphql)

class VideoYouTubeOptionSource(KineticLambdaDataSource):
  @property
  def code(self)->lambda_.Code:
    return lambda_.Code.from_asset(path.join(ROOT_DIR,'src/data/get-video-download'))

  @property
  def type_name(self)->str:
    return 'Video'
  
  @property
  def field_name(self)->str:
    return 'youtube_opts'

  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure, graphql:appsync.IGraphqlApi) -> None:
    super().__init__(scope, id, infra, graphql)

class VideoCachedSource(KineticLambdaDataSource):
  @property
  def code(self)->lambda_.Code:
    return lambda_.Code.from_asset(path.join(ROOT_DIR,'src/data/get-video-cache'))

  @property
  def type_name(self)->str:
    return 'Video'
  
  @property
  def field_name(self)->str:
    return 'cached'

  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure, graphql:appsync.IGraphqlApi) -> None:
    super().__init__(scope, id, infra, graphql)


class VideoAnalysisSource(KineticLambdaDataSource):
  @property
  def code(self)->lambda_.Code:
    return lambda_.Code.from_asset(path.join(ROOT_DIR,'src/data/get-video-analysis'))

  @property
  def type_name(self)->str:
    return 'Video'
  
  @property
  def field_name(self)->str:
    return 'analysis'

  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure, graphql:appsync.IGraphqlApi, annotation_table:ddb.ITable) -> None:
    super().__init__(scope, id, infra, graphql, environment={
      'ANNOTATION_TABLE':annotation_table.table_name
    })

    annotation_table.grant_read_data(self.function)

class DataPlaneConstruct(Construct):
  def __init__(self, scope: Construct, id: str, infra:IBaseInfrastructure) -> None:
    super().__init__(scope, id)

    self.infra = infra
    self.graphql = appsync.GraphqlApi(self,'GraphQL',
      name='kinetic-graphql',
      schema= appsync.SchemaFile.from_asset(path.join(ROOT_DIR,'src/data/schema.graphql')),
      log_config=appsync.LogConfig(
        field_log_level= appsync.FieldLogLevel.ALL,
        retention= logs.RetentionDays.FIVE_DAYS
      ),
      # authorization_config=appsync.AuthorizationConfig(
      #   default_authorization=appsync.AuthorizationMode(
      #     authorization_type= appsync.AuthorizationType.
      #   ).API_KEY),
      xray_enabled=True)

    annotations = AnnotationDataSource(self,'Annotations',infra=infra, graphql=self.graphql)
    VideoDataSource(self,'Video',infra=infra, graphql=self.graphql)
    PeopleDataSource(self,'People',infra=infra, graphql=self.graphql)
    VideoYouTubeOptionSource(self,'YouTubeOptions',infra=infra, graphql=self.graphql)
    VideoCachedSource(self,'VideoCached',infra=infra, graphql=self.graphql)
    VideoAnalysisSource(self,'VideoAnalysis',infra=infra, graphql=self.graphql, annotation_table=annotations.annotation_table)
