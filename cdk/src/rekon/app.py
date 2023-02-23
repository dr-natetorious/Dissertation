#!/usr/bin/env python3
import boto3
from config import Config
from json import dumps
from analyze import Analyzer
from skeleton import SkeletonManifest
from botocore.exceptions import ClientError
from status import StatusTable, ActionStatus
from botocore.exceptions import ClientError
from aws_xray_sdk.core import xray_recorder, patch_all
patch_all()

status_table = StatusTable(Config.STATUS_TABLE)

@xray_recorder.capture('lambda_function')
def lambda_function(event, _=None)->dict:
  invocation_id = event['invocationId']
  results = []
  for task in event['tasks']:
    task_id = task['taskId']
    bucket_name = task['s3BucketArn'].split(':')[-1]
    object_key = task['s3Key']

    manifest = SkeletonManifest(bucket_name,object_key)

    status, lastModified = status_table.get_process_status(manifest.video_id)
    # if status == ActionStatus.COMPLETE:
    #   results.append({
    #     'taskId': task_id,
    #     'resultCode': 'Succeeded',
    #     'resultString': ''
    #   })
    #   continue

    analyzer = Analyzer(manifest)
    analyzer.process()
    
    # status_table.set_process_status(manifest.video_id, ActionStatus.COMPLETE)
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
            "s3Key": "extract/-2gHxh_3BDc/skeletons.json",
            "s3VersionId": "1",
            "s3BucketArn": "arn:aws:s3:::data.dissertation.natetorio.us"
        }
    ]  
  })