#!/usr/bin/env python3

import aws_cdk as cdk
from constructs import Construct
from stacks.data_collection import DataCollectionConstruct
from stacks.base_infra import BaseInfrastructureConstruct
from stacks.analyze_video import VideoProcessorConstruct
from stacks.extractor import MovementExtractorConstruct

class KineticStack(cdk.Stack):
  def __init__(self, scope: Construct, id:str, **kwargs):
    super().__init__(scope,id, **kwargs)

    infra = BaseInfrastructureConstruct(self,'Infrastructure')
    
    DataCollectionConstruct(self,'DataCollection', infra=infra)
    VideoProcessorConstruct(self,'VideoProcessor', infra=infra)
    MovementExtractorConstruct(self,'MovementExtractor', infra=infra)


class KineticApp(cdk.App):
  def __init__(self, **kwargs)->None:
    super().__init__(**kwargs)

    env = cdk.Environment(account='995765563608', region='us-east-2')
    KineticStack(self,'Kinetic', env=env)

app = KineticApp()
app.synth()