import builtins
from typing import List
from stacks.interfaces import INetworkConstruct, IBaseInfrastructure, IComputeConstruct, IDataStorage
from stacks.infra_events import ApplicationEventsConstruct
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import(
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_s3 as s3,
    aws_iam as iam,
    aws_secretsmanager as sm,
    aws_redshiftserverless as rs,
)

class NetworkConstruct(Construct, INetworkConstruct):
  
  @property
  def vpc(self)->ec2.IVpc:
    return self.__vpc

  @vpc.setter
  def vpc(self, value)->ec2.IVpc:
    self.__vpc =value

  @property
  def open_security_group(self)->ec2.ISecurityGroup:
    return self.__open_security_group

  @open_security_group.setter
  def open_security_group(self,value)->None:
    self.__open_security_group = value
  
  def __init__(self, scope: Construct, id: builtins.str) -> None:
    super().__init__(scope, id)
    self.gateways=dict()
    self.interfaces=dict()

    self.vpc = ec2.Vpc(self,'Vpc',
      max_azs=2, 
      ip_addresses= ec2.IpAddresses.cidr(cidr_block='10.30.0.0/16'),
      subnet_configuration=[
        ec2.SubnetConfiguration(name='Default', subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=20),
        ec2.SubnetConfiguration(name='Public', subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24,map_public_ip_on_launch=True),
        ec2.SubnetConfiguration(name='Vpn', subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24)
      ])

    self.open_security_group = ec2.SecurityGroup(self,'OpenMarriage',
      vpc= self.vpc,
      allow_all_outbound=True,
      allow_all_ipv6_outbound=True,
      description='Default No Firewall')

    self.add_gateways()
    self.add_ssm_support()

  def add_gateways(self):
    for svc in ['s3', 'dynamodb']:
      self.gateways[svc] = ec2.GatewayVpcEndpoint(
        self, svc,
        vpc=self.vpc,
        service=ec2.GatewayVpcEndpointAwsService(
          name=svc))
    return self

  def add_rekognition_support(self):
    return self.add_interfaces(services=[
      'rekognition'
    ])

  def add_textract_support(self):
    return self.add_interfaces(services=[
      'textract'
    ])

  def add_kms_support(self):
    return self.add_interfaces(services=[
      'kms'
    ])

  def add_ssm_support(self):
    return self.add_interfaces(services=[
      'ssm', 'ec2messages', 'ec2','ssmmessages','logs'
    ])

  def add_lambda_support(self):
    return self.add_interfaces(services=[
      'elasticfilesystem', 'lambda', 'states',
      'ecr.api', 'ecr.dkr'
    ])

  def add_apigateway_support(self):
    return self.add_interfaces(services=[
      'execute-api'
    ])

  def add_storage_gateway(self):
    return self.add_interfaces(services=[
      'storagegateway'
    ])

  def add_everything(self):
    return self.add_interfaces(services=[
      'ssm', 'ec2messages', 'ec2',
      'ssmmessages', 'kms', 'elasticloadbalancing',
      'elasticfilesystem', 'lambda', 'states',
      'events', 'execute-api', 'kinesis-streams',
      'kinesis-firehose', 'logs', 'sns', 'sqs',
      'secretsmanager', 'config', 'ecr.api', 'ecr.dkr',
      'storagegateway'
    ])

  def add_interfaces(self, services:List[str]):
    for svc in services:
      if not svc in self.interfaces:
        self.interfaces[svc] = ec2.InterfaceVpcEndpoint(
          self, svc,
          vpc=self.vpc,
          service=ec2.InterfaceVpcEndpointAwsService(name=svc),
          open=True,
          private_dns_enabled=True,
          lookup_supported_azs=True,
          security_groups=[self.open_security_group])

class ComputeConstruct(Construct, IComputeConstruct):

  @property
  def fargate_cluster(self)->ecs.ICluster:
    return self.__fargate_cluster

  def __init__(self, scope: Construct, id: builtins.str, network:INetworkConstruct, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.__fargate_cluster = ecs.Cluster(self,'Fargate',
      enable_fargate_capacity_providers=True,
      cluster_name='kinetic',
      container_insights=True,
      vpc=network.vpc)

class RedshiftConstruct(Construct):
  def __init__(self, scope: Construct, id: builtins.str, network:NetworkConstruct) -> None:
    super().__init__(scope, id)
    cdk.Tags.of(self).add(key='construct',value=RedshiftConstruct.__name__)

    self.secret = sm.Secret(self,'Password',
      description='Password to Redshift cluster',
      generate_secret_string= sm.SecretStringGenerator(
        exclude_punctuation=True,
        password_length=32
      ))

    self.roles = list()
    for service in ['redshift-serverless', 'redshift', 'sagemaker']:
      role = iam.Role(self,service + 'Role',
        role_name='dissertation.redshift.%s.%s' % (
          service,
          cdk.Aws.REGION,
        ),
        assumed_by=iam.ServicePrincipal(service),
        managed_policies=[
          iam.ManagedPolicy.from_aws_managed_policy_name('AmazonRedshiftAllCommandsFullAccess'),
          iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess')
        ])
      self.roles.append(role)

    self.namespace = rs.CfnNamespace(self,'Namespace',
      namespace_name='dissertation',
      admin_username='admin',
      admin_user_password=self.secret.secret_value.to_string(),
      iam_roles=[x.role_arn for x in self.roles],
      db_name='analytics'
      )

    self.security_group = ec2.SecurityGroup(self,'SecurityGroup',
      vpc = network.vpc,
      allow_all_outbound=True,
      description='Default SG for Redshift cluster')
    self.security_group.add_ingress_rule(
      peer=ec2.Peer.any_ipv4(),
      connection= ec2.Port.tcp_range(5431,5455))
    self.security_group.add_ingress_rule(
      peer=ec2.Peer.any_ipv4(),
      connection= ec2.Port.tcp_range(8191,8215))

    #subnets = [x.subnet_id for x in network.vpc.select_subnets(subnet_group_name='Default').subnets]
    subnets = [x.subnet_id for x in network.vpc.select_subnets().subnets]

    self.workgroup = rs.CfnWorkgroup(self,'Workgroup',
      workgroup_name='dissertation-workgroup',
      enhanced_vpc_routing=True,
      security_group_ids=[self.security_group.security_group_id],
      subnet_ids= subnets,
      namespace_name='dissertation',
      )

class DataStorageConstruct(Construct):
  
  @property
  def data_bucket(self)->s3.IBucket:
    return self.__data_bucket

  @property
  def inventory_bucket(self)->s3.IBucket:
    return self.__inventory_bucket

  @property
  def movement_bucket(self)->s3.IBucket:
    return self.__movement_bucket

  def __init__(self, scope: Construct, id: builtins.str, network:INetworkConstruct) -> None:
    super().__init__(scope, id)

    self.__data_bucket = s3.Bucket.from_bucket_name(self,'DataBucket', 
      bucket_name='data.dissertation.natetorio.us')

    self.__inventory_bucket = s3.Bucket.from_bucket_name(self,'InventoryBucket', 
      bucket_name='inventory.us-east-2.dissertation.natetorio.us')

    self.__movement_bucket = s3.Bucket(self,'Bucket',
      bucket_name='movement.us-east-2.dissertation.natetorio.us')

    #self.__redshift = RedshiftConstruct(self,'Redshift', network=network)

class BaseInfrastructureConstruct(Construct, IBaseInfrastructure):
  
  @property
  def network(self)->INetworkConstruct:
    return self.__network

  @property
  def storage(self)->IDataStorage:
    return self.__storage

  @property
  def compute(self)->IComputeConstruct:
    return self.__compute
  
  @property
  def events(self)->ApplicationEventsConstruct:
    return self.__events
  
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope,id,**kwargs)
    
    self.__network = NetworkConstruct(self,'Network')
    self.__storage = DataStorageConstruct(self,'Storage', network=self.__network)
    self.__compute = ComputeConstruct(self,'Compute', network=self.__network)

    self.__events = ApplicationEventsConstruct(self,'ApplicationEvents')

    return