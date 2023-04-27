import builtins
from os import path
import aws_cdk as cdk
from json import dumps
from stacks.interfaces import IBaseInfrastructure
from constructs import Construct
from aws_cdk import(
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_appsync as appsync,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_logs as logs,
    aws_dynamodb as ddb,
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as e_targets,
)


ROOT_DIR = path.join(path.dirname(__file__),'..')

def fetch_ddb_attribute(field):
  return '''
  {
    "version": "2017-02-28",
    "operation": "GetItem",
    "key": {
      "VideoId": $util.dynamodb.toDynamoDBJson($ctx.arguments.id)
    },
    "projectionExpression": "%s"
  }
  '''.format(field)

def return_ddb_attribute(field):
  return '''
  #if($ctx.result.item)
    #set($value = $ctx.result.item.%%s)
    #if($value)
      {'label':'fred', 'value':"$value" }
    #else
      null
    #end
  #else
    null
  #end
  '''.format(field).strip()

class AnnotationDataSource(Construct):
  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure, graphql:appsync.IGraphqlApi) -> None:
    super().__init__(scope, id)

    annotation_table = ddb.Table(self,'Table',
      table_name='video-annotations',
      billing_mode= ddb.BillingMode.PAY_PER_REQUEST,
      removal_policy = cdk.RemovalPolicy.DESTROY,
      partition_key= ddb.Attribute(name='VideoId', type=ddb.AttributeType.STRING))

    # dynamodb_ds =appsync.DynamoDbDataSource(self,'DynamoSource',
    #   api=graphql,
    #   table=annotation_table,
    #   read_only_access=True,
    #   service_role=iam.Role(self,'DynamoRole',
    #     assumed_by=iam.ServicePrincipal('appsync.amazonaws.com'),
    #     managed_policies=[
    #       iam.ManagedPolicy.from_aws_managed_policy_name('AmazonDynamoDBFullAccess')
    #     ]))
    
    # dynamodb_ds.create_resolver('GetAnnotation',
    #   type_name='Query',
    #   field_name='get_annotation',
    #   request_mapping_template=appsync.MappingTemplate.dynamo_db_get_item(key_name='VideoId',id_arg='id'),
    #   response_mapping_template=appsync.MappingTemplate.from_string(return_ddb_attribute('label')))


    function = lambda_.Function(self,'Function',
      function_name='kinetic-graphql-annotations',
      code=lambda_.Code.from_asset(path.join(ROOT_DIR,'src/data/get-annotations')),
      handler='index.lambda_function',
      runtime= lambda_.Runtime.PYTHON_3_9,
      environment={
        'TABLE_NAME': annotation_table.table_name
      })
    
    annotation_table.grant_read_data(function)
    #function.grant_invoke(iam.ServicePrincipal(service='appsync.amazonaws.com'))

    # annotations_source = graphql.add_dynamo_db_data_source('DynamoDBSource',
    #   name='annotations_source',
    #   table=annotation_table,
    #   description='Annotation Information')
    
    lambda_source = graphql.add_lambda_data_source('LambdaSource',
      name='AnnotationQuerySource',
      lambda_function=function)
    
    graphql.create_resolver('GetAnnotation',
      type_name='Query',
      field_name='get_annotation',
      data_source=lambda_source,
      request_mapping_template=appsync.MappingTemplate.lambda_request(),
      response_mapping_template=appsync.MappingTemplate.lambda_result())

    # annotations_source.create_resolver('LabelResolver',
    #   type_name='Annotation',
    #   field_name='label',
    #   request_mapping_template= appsync.MappingTemplate.dynamo_db_get_item(
    #     key_name='PartitionKey',
    #     id_arg='id'
    #   ),
    #   response_mapping_template=appsync.MappingTemplate.from_string(return_ddb_attribute('label')))
    
    # annotations_source.create_resolver('SegmentResolver',
    #   type_name='Annotation',
    #   field_name='segment',
    #   request_mapping_template= appsync.MappingTemplate.dynamo_db_get_item(
    #     key_name='PartitionKey',
    #     id_arg='id'
    #   ),
    #   response_mapping_template=appsync.MappingTemplate.from_string(return_ddb_attribute('segment')))

class DataPlaneConstruct(Construct):
  def __init__(self, scope: Construct, id: str, infra:IBaseInfrastructure) -> None:
    super().__init__(scope, id)

    self.graphql = appsync.GraphqlApi(self,'GraphQL',
      name='kinetic-graphql',
      schema= appsync.SchemaFile.from_asset(path.join(ROOT_DIR,'src/data/schema.graphql')),
      # authorization_config=appsync.AuthorizationConfig(
      #   default_authorization=appsync.AuthorizationMode(
      #     authorization_type= appsync.AuthorizationType.
      #   ).API_KEY),
      xray_enabled=True)

    AnnotationDataSource(self,'Annotations',infra=infra, graphql=self.graphql)
