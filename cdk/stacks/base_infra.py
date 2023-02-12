import builtins
from typing import List
from stacks.interfaces import INetworkConstruct, IBaseInfrastructure, IComputeConstruct, IDataStorage
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import(
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_s3 as s3,
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

class DataStorageConstruct(Construct):
  
  @property
  def data_bucket(self)->s3.IBucket:
    return self.__data_bucket

  @property
  def inventory_bucket(self)->s3.IBucket:
    return self.__inventory_bucket

  def __init__(self, scope: Construct, id: builtins.str) -> None:
    super().__init__(scope, id)

    self.__data_bucket = s3.Bucket.from_bucket_name(self,'DataBucket', 
      bucket_name='data.dissertation.natetorio.us')

    self.__inventory_bucket = s3.Bucket.from_bucket_name(self,'InventoryBucket', 
      bucket_name='inventory.us-east-2.dissertation.natetorio.us')

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
  
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope,id,**kwargs)
    
    self.__network = NetworkConstruct(self,'Network')
    self.__storage = DataStorageConstruct(self,'Storage')
    self.__compute = ComputeConstruct(self,'Compute', network=self.__network)
    return