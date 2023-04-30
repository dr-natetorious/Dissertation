#!/usr/bin/env python3

import aws_cdk as cdk
from constructs import Construct
from stacks.data_collection import DataCollectionConstruct
from stacks.infra_base import BaseInfrastructureConstruct
from stacks.analyze_video_gpu import VideoProcessorConstruct
from stacks.extractor import MovementExtractorConstruct
from stacks.api import ControlPlaneConstruct
from stacks.rekon import RekognitionConstruct
from stacks.data_plane import DataPlaneConstruct

class KineticStack(cdk.Stack):
  def __init__(self, scope: Construct, id:str, **kwargs):
    super().__init__(scope,id, **kwargs)

    infra = BaseInfrastructureConstruct(self,'Infrastructure')
    
    DataCollectionConstruct(self,'DataCollection', infra=infra)
    VideoProcessorConstruct(self,'VideoProcessor', infra=infra)
    MovementExtractorConstruct(self,'MovementExtractor', infra=infra)
    ControlPlaneConstruct(self,'ControlPlane', infra=infra)

    DataPlaneConstruct(self,'DataPlane', infra=infra)
    RekognitionConstruct(self,'Rekon', infra=infra)


class KineticApp(cdk.App):
  def __init__(self, **kwargs)->None:
    super().__init__(**kwargs)

    env = cdk.Environment(account='995765563608', region='us-east-2')
    KineticStack(self,'Kinetic', env=env)

app = KineticApp()
app.synth()