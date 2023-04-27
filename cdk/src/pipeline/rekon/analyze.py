import boto3
from time import sleep
from random import randint
from botocore.exceptions import ClientError
from json import dumps, loads
from typing import List
from config import Config
from status import StatusTable, ActionStatus
from skeleton import SkeletonManifest, Frame
from aws_xray_sdk.core import xray_recorder

s3 = boto3.client('s3', region_name=Config.REGION_NAME)
kinesis= boto3.client('kinesis', region_name=Config.REGION_NAME)
status_table = StatusTable(Config.STATUS_TABLE)

valid_regions = ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'eu-central-1','eu-west-1','eu-west-2', 'ap-south-1', 'ap-northeast-2','ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1']


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

  @xray_recorder.capture('Analyzer::detect_labels')
  def __detect_labels_with_retry(self, **kwargs)->dict:

    for _ in range(0, 5):
      try:
        region = valid_regions[randint(0,len(valid_regions)-1)]
        rekognition = boto3.client('rekognition', region_name=region)

        print('DetectLabels(%s) - s3://%s -> %s' % (
          region,
          self.manifest.report.frame_bucket,
          self.manifest.video_id
        ))
    
        return rekognition.detect_labels(**kwargs)
      except rekognition.exceptions.ProvisionedThroughputExceededException as error:
        print('ProvisionedThroughputExceededException -- %s' % str(error))
        sleep(randint(10,50)/10)
    raise Exception('Unable to detect_labels - %s' % self.manifest.video_id)

  @xray_recorder.capture('Analyzer::detect_labels')
  def __detect_faces_with_retry(self, **kwargs)->dict:

    for _ in range(0, 5):
      try:
        region = valid_regions[randint(0,len(valid_regions)-1)]
        rekognition = boto3.client('rekognition', region_name=region)

        print('DetectFaces(%s) - s3://%s -> %s' % (
          region,
          self.manifest.report.frame_bucket,
          self.manifest.video_id
        ))
    
        return rekognition.detect_faces(**kwargs)
      except rekognition.exceptions.ProvisionedThroughputExceededException as error:
        print('ProvisionedThroughputExceededException -- %s' % str(error))
        sleep(randint(10,50)/10)
    raise Exception('Unable to detect_labels - %s' % self.manifest.video_id)

  @xray_recorder.capture('Analyzer::sample_frame')
  def __sample_frame(self, frame:Frame)->dict:
    labels = self.__sample_frame_labels(frame)
    faces = self.__sample_frame_faces(frame)

    kinesis.put_records(
      StreamName=Config.REPORT_STREAM,
      Records=[
        {
          'PartitionKey': frame.source_uri,
          'Data': dumps({
              'Offset': frame.offset,
              'VideoId': frame.parent.parent.video_id,
              'Location':{
                'SourceUri': frame.source_uri,
                'OpenPoseUri': frame.annotated_uri
              },
              'FaceDetails': faces['FaceDetails'],
              'Labels': labels['Labels']
            }).encode('utf-8'),
        },
      ])

    return {
      'Offset': frame.offset,
      'Location':{
        'SourceUri': frame.source_uri,
        'OpenPoseUri': frame.annotated_uri
      },
      'FaceDetails': faces['FaceDetails'],
      'Labels': labels['Labels']
    }

  @xray_recorder.capture('Analyzer::sample_frame')
  def __sample_frame_faces(self, frame:Frame)->dict:
    status, lastModified = status_table.get_frame_face_status(
      self.manifest.video_id,
      frame.source_uri)

    if status == ActionStatus.COMPLETE:
      response = s3.get_object(
        Bucket=self.manifest.report.frame_bucket,
        Key= 'rekognition/detect_faces/%s' % frame.source_uri,
      )
      response = loads(response['Body'].read())
    else:
      image = s3.get_object(
        Bucket=self.manifest.report.frame_bucket,
        Key=frame.source_uri
      )

      response = self.__detect_faces_with_retry(
        Image={
          # 'S3Object':{
          #   'Bucket': self.manifest.report.frame_bucket,
          #   'Name': frame.source_uri
          # },
          'Bytes': image['Body'].read()
        },
        Attributes=['ALL']
      )

      s3.put_object(
        Bucket=self.manifest.report.frame_bucket,
        Key= 'rekognition/detect_faces/%s' % frame.source_uri,
        Body=dumps(response, indent=2),
        Metadata={
          'VideoId': self.manifest.video_id,
          'TotalFaces': str(len(response['FaceDetails']))
        })
      
      status_table.set_frame_face_status(
        self.manifest.video_id,
        frame.source_uri,
        ActionStatus.COMPLETE
      )

    return {
      'Offset': frame.offset,
      'VideoId': frame.parent.parent.video_id,
      'Action': 'DetectFaces',
      'Location':{
        'SourceUri': frame.source_uri,
        'OpenPoseUri': frame.annotated_uri
      },
      'FaceDetails': response['FaceDetails'],
    }

  @xray_recorder.capture('Analyzer::sample_frame')
  def __sample_frame_labels(self, frame:Frame)->dict:
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
      image = s3.get_object(
        Bucket=self.manifest.report.frame_bucket,
        Key=frame.source_uri
      )

      response = self.__detect_labels_with_retry(
        Image={
          # 'S3Object':{
          #   'Bucket': self.manifest.report.frame_bucket,
          #   'Name': frame.source_uri
          # },
          'Bytes': image['Body'].read()
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
        frame.source_uri,
        ActionStatus.COMPLETE
      )

    return {
      'Offset': frame.offset,
      'VideoId': frame.parent.parent.video_id,
      'Action': 'DetectLabels',
      'Location':{
        'SourceUri': frame.source_uri,
        'OpenPoseUri': frame.annotated_uri
      },
      'Labels': response['Labels'],
      'LabelModelVersion': response['LabelModelVersion']
    }
