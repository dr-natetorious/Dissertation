import builtins
from stacks.interfaces import INetworkConstruct, IBaseInfrastructure
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import(
    aws_ec2 as ec2,    
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

class BaseInfrastructureConstruct(Construct, IBaseInfrastructure):
  
  @property
  def network(self)->INetworkConstruct:
    return self.__network
  
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope,id,**kwargs)
    
    self.__network = NetworkConstruct(self,'Network')
    return