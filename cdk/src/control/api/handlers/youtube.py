import boto3
from flask import Blueprint, request
from config import Config
from json import loads, dumps
from status import StatusTable, ActionStatus

MAX_SQS_BATCH_SIZE = 10

youtube_api = Blueprint('youtube_api', __name__)

s3 = boto3.client('s3', region_name=Config.REGION_NAME)
rekognition = boto3.client('rekognition', region_name=Config.REGION_NAME)
sqs = boto3.client('sqs', region_name=Config.REGION_NAME)

@youtube_api.route('/youtube/download/<videoid>')
def download_video(videoid:str):
  return batch_send_dataset(videoid)

def batch_send_dataset(name:str)->None:
  dataset = get_json_file(name)
  keys = list(dataset.keys())
  total_successful=0
  for ix in range(0,len(keys), MAX_SQS_BATCH_SIZE):
    batch = keys[ix:ix+MAX_SQS_BATCH_SIZE]

    response = sqs_client.send_message_batch(
      QueueUrl=SQS_QUEUE_URL,
      Entries=[
        {
          'Id': m,
          #'MessageDeduplicationId': m,
          #'MessageGroupId': dataset[m]['annotations']['label'],
          'MessageBody': dumps({
            'video_id':m,
            'properties': dataset[m]
          })
        } for m in batch
      ])

    if 'Failed' in response:
      display_error_response(response)
    if 'Successful' in response:
      total_successful = display_successful_response(response, total_successful)
