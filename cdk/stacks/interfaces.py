from aws_cdk import(
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_sqs as sqs,
    aws_s3 as s3,
    aws_dynamodb as ddb,
)

class INetworkConstruct:
    @property
    def vpc(self)->ec2.IVpc:
        raise NotImplementedError()

class IComputeConstruct:
    @property
    def fargate_cluster(self)->ecs.ICluster:
        raise NotImplementedError()

class IDataStorage:
    @property
    def data_bucket(self)->s3.IBucket:
        raise NotImplementedError()

class IBaseInfrastructure:
    @property
    def network(self)->INetworkConstruct:
        raise NotImplementedError()

    # @property
    # def compute(self)->IComputeConstruct:
    #     raise NotImplementedError()

    @property
    def storage(self)->IDataStorage:
        raise NotImplementedError()

class IQueuedTask:
    @property
    def task_queue(self)->sqs.IQueue:
        raise NotImplementedError()    

class IDataCollection:
    @property
    def youtube(self) -> IQueuedTask:
        raise NotImplementedError()