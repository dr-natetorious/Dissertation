#!/usr/bin/env python3
import boto3
from config import Config
from json import dumps
from os import path
from status import StatusTable, ExtractStatus
from botocore.exceptions import ClientError
from report import Report, NoFramesException
from aws_xray_sdk.core import xray_recorder, patch_all
from tracer import MovementTracker
patch_all()

def videoid_from_url(object_key:str)->str:
  return path.basename(object_key).split('.')[0]

sqs = boto3.client('sqs', region_name=Config.REGION_NAME)
status_table = StatusTable(Config.STATUS_TABLE)

@xray_recorder.capture('fetch_video')
def fetch_video(bucket, object_key):
  sqs.send_message(
    QueueUrl=Config.FETCH_QUEUE,
    MessageBody=dumps({
      'VideoId': videoid_from_url(object_key),
      'RefLocation':{
        'Bucket': bucket,
        'Key': object_key
      }
    })
  )

@xray_recorder.capture('lambda_function')
def lambda_function(event, _=None)->dict:
  invocation_id = event['invocationId']
  results = []
  for task in event['tasks']:
    task_id = task['taskId']
    bucket_name = task['s3BucketArn'].split(':')[-1]
    object_key = task['s3Key']
    video_id = videoid_from_url(object_key)

    status, lastModified = status_table.get_extract_status(video_id)
    if status == ExtractStatus.COMPLETE:
      results.append({
        'taskId': task_id,
        'resultCode': 'Succeeded',
        'resultString': ''
      })
      continue

    try:
      report = Report(bucket_name, object_key)      
    except NoFramesException:
      results.append({
        'taskId': task_id,
        'resultCode': 'PermanentFailure',
        'resultString': 'NoFramesException'
      })
      continue
    except ClientError as error:
      if error.response['Error']['Code'] == 'NoSuchKey':
        fetch_video(bucket_name, object_key)
        results.append({
          'taskId': task_id,
          'resultCode': 'PermanentFailure',
          'resultString': 'FetchVideoRequested'
        })
        continue
      else:
        raise

    tracker = MovementTracker(report)
    tracker.save()
    status_table.set_extract_status(video_id, ExtractStatus.COMPLETE)
    results.append({
      'taskId': task_id,
      'resultCode': 'Succeeded',
      'resultString': ''
    })

  return {
    'invocationSchemaVersion': "1.0",
    'treatMissingKeyAs': 'PermanentFailure',
    'invocationId': invocation_id,
    'results': results 
  }


if __name__ == '__main__':
  xray_recorder.begin_segment('Main')
  lambda_function({
    "invocationSchemaVersion": "1.0",
    "invocationId": "YXNkbGZqYWRmaiBhc2RmdW9hZHNmZGpmaGFzbGtkaGZza2RmaAo",
    "job": {
        "id": "f3cc4f60-61f6-4a2b-8a21-d07600c373ce"
    },
    "tasks": [
        {
            "taskId": "dGFza2lkZ29lc2hlcmUK",
            "s3Key": "report/square+dancing/wGwVDCoUzoYzzzz.json",
            "s3VersionId": "1",
            "s3BucketArn": "arn:aws:s3:::data.dissertation.natetorio.us"
        }
    ]  
  })