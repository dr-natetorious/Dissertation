import builtins
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
  
  def __init__(self, scope: Construct, id: builtins.str) -> None:
    super().__init__(scope, id)

    self.__vpc = ec2.Vpc(self,'Vpc',
      max_azs=2, 
      ip_addresses= ec2.IpAddresses.cidr(cidr_block='10.30.0.0/16'),
      subnet_configuration=[
        ec2.SubnetConfiguration(name='Default', subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=20),
        ec2.SubnetConfiguration(name='Public', subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24,map_public_ip_on_launch=True),
        ec2.SubnetConfiguration(name='Vpn', subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24)
      ])

class ComputeConstruct(Construct, IComputeConstruct):

  @property
  def fargate_cluster(self)->ecs.ICluster:
    return self.__fargate_cluster

  def __init__(self, scope: Construct, id: builtins.str, infra:IBaseInfrastructure, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.__fargate_cluster = ecs.Cluster(self,'FargateCluster',
      enable_fargate_capacity_providers=True,
      container_insights=True,
      vpc=infra.network.vpc,
      capacity= ecs.AddCapacityOptions(
        vpc_subnets= ec2.SubnetSelection(subnet_group_name='Default')
      ))

class DataStorageConstruct(Construct):
  
  @property
  def data_bucket(self)->s3.IBucket:
    return self.__data_bucket

  def __init__(self, scope: Construct, id: builtins.str) -> None:
    super().__init__(scope, id)

    self.__data_bucket = s3.Bucket.from_bucket_name(self,'DataBucket', 
      bucket_name='data.dissertation.natetorio.us')

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
    #self.__compute = ComputeConstruct(self,'Compute')
    return