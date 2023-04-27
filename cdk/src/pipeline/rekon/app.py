#!/usr/bin/env python3
import boto3
from config import Config
from json import dumps, loads
from analyze import Analyzer
from skeleton import SkeletonManifest
from botocore.exceptions import ClientError
from status import StatusTable, ActionStatus
from botocore.exceptions import ClientError
from aws_xray_sdk.core import xray_recorder, patch_all
patch_all()

status_table = StatusTable(Config.STATUS_TABLE)
sqs = boto3.client('sqs', region_name=Config.REGION_NAME)

@xray_recorder.capture('s3_batch_event')
def s3_batch_event(event, _=None)->dict:
  invocation_id = event['invocationId']
  results = []
  for task in event['tasks']:
    task_id = task['taskId']
    bucket_name = task['s3BucketArn'].split(':')[-1]
    object_key = task['s3Key']

    manifest = SkeletonManifest(bucket_name,object_key)

    # status, lastModified = status_table.get_process_status(manifest.video_id)
    # if status == ActionStatus.COMPLETE:
    #   results.append({
    #     'taskId': task_id,
    #     'resultCode': 'Succeeded',
    #     'resultString': ''
    #   })
    #   continue

    analyzer = Analyzer(manifest)

    try:      
      analyzer.process()
    except ClientError as error:
      if error.response['Error']['Code'] == 'NoSuchKey':
        results.append({
          'taskId': task_id,
          'resultCode': 'Succeeded',
          'resultString': 'NoSuchKey - Skipping'
        })
      else:
        sqs.send_message(
          QueueUrl = Config.QUEUE_URL,
          MessageBody=dumps({
            'bucket': bucket_name,
            'object_key': object_key
          }))
        
        results.append({
          'taskId': task_id,
          'resultCode': 'TemporaryFailure',
          'resultString': str(error)
        })
      continue
    
    
    status_table.set_process_status(manifest.video_id, ActionStatus.COMPLETE)
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

@xray_recorder.capture('sqs_event')
def sqs_event(event, _)->dict:
  for record in event['Records']:
    receiptHandle = record['receiptHandle']

    body = loads(record['body'])

    bucket_name = body['bucket']
    object_key = body['object_key']

    manifest = SkeletonManifest(bucket_name,object_key)

    status, lastModified = status_table.get_process_status(manifest.video_id)
    analyzer = Analyzer(manifest)

    try:      
      analyzer.process()
    except ClientError as error:
      if error.response['Error']['Code'] == 'NoSuchKey':
        print('NoSuchKey(s3://%s/%s)' % (bucket_name, object_key))
    
    sqs.delete_message(
      QueueUrl=Config.QUEUE_URL,
      ReceiptHandle=receiptHandle)


@xray_recorder.capture('lambda_function')
def lambda_function(event, context=None)->dict:
  if 'invocationId' in event:
    return s3_batch_event(event, context)
  elif 'Records' in event:
    return sqs_event(event, context)

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
            "s3Key": "extract/-2gHxh_3BDc/skeletons.json",
            "s3VersionId": "1",
            "s3BucketArn": "arn:aws:s3:::data.dissertation.natetorio.us"
        }
    ]  
  })