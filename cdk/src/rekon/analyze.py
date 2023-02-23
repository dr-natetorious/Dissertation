import boto3
from json import dumps, loads
from typing import List
from config import Config
from status import StatusTable, ActionStatus
from skeleton import SkeletonManifest, Frame
from aws_xray_sdk.core import xray_recorder

s3 = boto3.client('s3', region_name=Config.REGION_NAME)
rekognition = boto3.client('rekognition', region_name=Config.REGION_NAME)
status_table = StatusTable(Config.STATUS_TABLE)

class Analyzer:
  def __init__(self, manifest:SkeletonManifest) -> None:
    self.manifest = manifest

  @xray_recorder.capture('Analyzer::Process')
  def process(self)->None:
    report = dict()
    report['VideoId'] =self.manifest.video_id
    report['Manifest'] = {
      'Bucket': self.manifest.bucket,
      'Key': self.manifest.object_key,
    }

    report['KeyFrames'] = {
      'Total': len(self.manifest.report.key_frames)
    }

    if len(self.manifest.report.key_frames) > 0:
      report['KeyFrames']['Sampled'] = self.__sample_key_frames()

    s3.put_object(
      Bucket=Config.DATA_BUCKET,
      Key='rekognition/analyze/%s.json' % self.manifest.video_id,
      Body=dumps(report, indent=2),
      Metadata={
        'VideoId': self.manifest.video_id
      }
    )

  @xray_recorder.capture('Analyzer::sample_key_frames')
  def __sample_key_frames(self)->List[dict]:
    first_frame = self.manifest.report.key_frames[0]
    return [ self.__sample_frame(first_frame) ]

  @xray_recorder.capture('Analyzer::sample_frame')
  def __sample_frame(self, frame:Frame)->dict:

    status, lastModified = status_table.get_frame_status(
      self.manifest.video_id,
      frame.source_uri)
    
    if status == ActionStatus.COMPLETE:
      response = s3.get_object(
        Bucket=self.manifest.report.frame_bucket,
        Key= 'rekognition/detect_labels/%s' % frame.source_uri,
      )
      response = loads(response['Body'].read())
    else:
      response = rekognition.detect_labels(
        Image={
          'S3Object':{
            'Bucket': self.manifest.report.frame_bucket,
            'Name': frame.source_uri
          },
        },
        MinConfidence=Config.MIN_CONFIDENCE
      )

      s3.put_object(
        Bucket=self.manifest.report.frame_bucket,
        Key= 'rekognition/detect_labels/%s' % frame.source_uri,
        Body=dumps(response, indent=2),
        Metadata={
          'VideoId': self.manifest.video_id
        }
      )
      status_table.set_frame_status(
        self.manifest.video_id,
        frame.source_uri
      )

    return {
      'Offset': frame.offset,
      'Location':{
        'SourceUri': frame.source_uri,
        'OpenPoseUri': frame.annotated_uri
      },
      'Labels': response['Labels'],
      'LabelModelVersion': response['LabelModelVersion']
    }
