#!/usr/bin/env python3

from report import Report
from aws_xray_sdk.core import xray_recorder, patch_all
from tracer import MovementTracker
patch_all()

@xray_recorder.capture('lambda_function')
def lambda_function(event, _)->dict:
  invocation_id = event['invocationId']
  results = []
  for task in event['tasks']:
    task_id = task['taskId']
    bucket_name = task['s3BucketArn'].split(':')[-1]
    object_key = task['s3Key']

    report = Report(bucket_name, object_key)
    tracker = MovementTracker(report)
    tracker.save()

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
  xray_recorder.begin_segment()
  lambda_function({
    "invocationSchemaVersion": "1.0",
    "invocationId": "YXNkbGZqYWRmaiBhc2RmdW9hZHNmZGpmaGFzbGtkaGZza2RmaAo",
    "job": {
        "id": "f3cc4f60-61f6-4a2b-8a21-d07600c373ce"
    },
    "tasks": [
        {
            "taskId": "dGFza2lkZ29lc2hlcmUK",
            "s3Key": "report/climbing a rope/U6rFyjVdg0k.json",
            "s3VersionId": "1",
            "s3BucketArn": "arn:aws:s3:::data.dissertation.natetorio.us"
        }
    ]  
  })