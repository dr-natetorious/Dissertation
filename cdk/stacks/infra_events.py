import builtins
from os import path
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import(
    aws_iam as iam,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_logs as logs,
    aws_dynamodb as ddb,
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as e_targets,
)

ROOT_DIR = path.join(path.dirname(__file__),'..')

class JobStatusChangedConstruct(Construct):
  def __init__(self, scope: Construct, id: builtins.str) -> None:
    super().__init__(scope, id)

    self.topic = sns.Topic(self,'Topic',
      topic_name=JobStatusChangedConstruct.__name__)
    
    debug_queue = sqs.Queue(self,'DebugQueue',
      retention_period= cdk.Duration.days(7))

    with open(path.join(ROOT_DIR,'src/control/job-status-handler/index.py'), 'rt') as f:
      self.job_status_handler = lambda_.Function(self,'JobStatusHandler',
        code = lambda_.InlineCode(f.read()),
        handler='index.function_handler',
        dead_letter_queue= debug_queue,
        runtime= lambda_.Runtime.PYTHON_3_9,
        environment={
          'TOPIC_ARN': self.topic.topic_arn
        })
      
    self.topic.grant_publish(self.job_status_handler.role)
    rule = events.Rule(self,'JobStatusChanged')
    rule.add_event_pattern(
      source= [
        "aws.s3"
      ],
      detail= {
        "eventSource": [
          "s3.amazonaws.com"
        ],
        "eventName": [
          "JobCreated",
          "JobStatusChanged"
        ]
    })

    #rule.add_target(e_targets.LambdaFunction(self.job_status_handler))
    rule.add_target(e_targets.SqsQueue(debug_queue))
    rule.add_target(e_targets.SnsTopic(self.topic))

class ApplicationEventsConstruct(Construct):
  def __init__(self, scope: Construct, id: builtins.str) -> None:
    super().__init__(scope, id)      

    self.job_status_changed = JobStatusChangedConstruct(self,'JobStatusChanged')