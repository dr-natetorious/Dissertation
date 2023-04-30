import boto3
from flask import Blueprint, request
from config import Config
from json import loads, dumps
from status import StatusTable, ActionStatus

detection_api = Blueprint('detection_api', __name__)

s3 = boto3.client('s3', region_name=Config.REGION_NAME)
rekognition = boto3.client('rekognition', region_name=Config.REGION_NAME)
status_table = StatusTable(Config.STATUS_TABLE)

@detection_api.route('/detect/labels')
def detect_labels():
  '''
  Handles the /detect/labels action
  '''
  bucket = request.json['Bucket']
  video_id = request.json['VideoId']
  object_key = request.json['Key']

  status, lastModified = status_table.get_frame_status(
    video_id,
    object_key)

  if status == ActionStatus.COMPLETE:
    response = s3.get_object(
      Bucket=bucket,
      Key= 'rekognition/detect_labels/%s' % object_key,
    )
    response = loads(response['Body'].read())
    return response
  else:
    image = s3.get_object(
      Bucket= bucket,
      Key= object_key
    )

    response = rekognition.detect_labels(
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
      Bucket=bucket,
      Key= 'rekognition/detect_labels/%s' % object_key,
      Body=dumps(response, indent=2),
      Metadata={
        'VideoId': video_id
      }
    )
    status_table.set_frame_status(
      video_id,
      object_key,
      ActionStatus.COMPLETE
    )
    return response

@detection_api.route('/detect/faces')
def detect_faces():
  '''
  Handles the /detect/faces action
  '''
  bucket = request.json['Bucket']
  video_id = request.json['VideoId']
  object_key = request.json['Key']

  status, lastModified = status_table.get_frame_face_status(
    video_id,
    object_key)

  if status == ActionStatus.COMPLETE:
    response = s3.get_object(
      Bucket=bucket,
      Key= 'rekognition/detect_faces/%s' % object_key,
    )
    response = loads(response['Body'].read())
    return response
  else:
    image = s3.get_object(
      Bucket=bucket,
      Key=object_key
    )

    response = rekognition.detect_faces(
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
      Bucket=bucket,
      Key= 'rekognition/detect_faces/%s' % object_key,
      Body=dumps(response, indent=2),
      Metadata={
        'VideoId': video_id,
        'TotalFaces': str(len(response['FaceDetails']))
      })
    
    status_table.set_frame_face_status(
      video_id,
      object_key,
      ActionStatus.COMPLETE
    )
    return response
