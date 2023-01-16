from aws_cdk import(
    aws_ec2 as ec2,    
    aws_sqs as sqs,
    aws_dynamodb as ddb,
)

class INetworkConstruct:
    @property
    def vpc(self)->ec2.IVpc:
        raise NotImplementedError()

class IBaseInfrastructure:
    @property
    def network(self)->INetworkConstruct:
        raise NotImplementedError()

class IYouTubeDownload:
    @property
    def task_queue(self)->sqs.IQueue:
        raise NotImplementedError()

    @property
    def status_table(self)->ddb.ITable:
        raise NotImplementedError()

class IDataCollection:
    @property
    def youtube(self) -> IYouTubeDownload:
        raise NotImplementedError()