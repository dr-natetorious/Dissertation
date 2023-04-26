import boto3
from flask import Blueprint, request
from config import Config
from json import loads, dumps
from status import StatusTable, ActionStatus

MAX_SQS_BATCH_SIZE = 10
SQS_QUEUE_URL = Config.OPENPOSE_QUEUE
skeleton_api = Blueprint('skeleton_api', __name__)

s3 = boto3.client('s3', region_name=Config.REGION_NAME)
rekognition = boto3.client('rekognition', region_name=Config.REGION_NAME)
sqs = boto3.client('sqs', region_name=Config.REGION_NAME)

@skeleton_api.route('/skeleton/start-extract/<videoid>')
def start_extract(videoid:str):
  response = sqs.send_message(
    QueueUrl=SQS_QUEUE_URL,
    Id= videoid,
    #'MessageDeduplicationId': m,
    #'MessageGroupId': dataset[m]['annotations']['label'],
    MessageBody= dumps({
      'video_id':videoid,
      'properties': dataset[m]
    }))
  
  return response

@skeleton_api.route('/skeleton/get-extract/<videoid>')
def get_extract(videoid:str):
  label = request.json['label']

  response = s3.get_object(
    Bucket=Config.DATA_BUCKET,
    Key='report/%s/%s.json'%(label,videoid)
  )

  return response['Body'].read()
