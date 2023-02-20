import boto3
from json import dumps
from os import environ

ACCOUNTID = environ.get('ACCOUNT_ID')
FUNCTION_ARN = environ.get('FUNCTION_ARN')
REPORT_BUCKET_ARN = environ.get('REPORT_BUCKET_ARN')
BATCH_ROLE_ARN = environ.get('BATCH_ROLE_ARN')

s3control = boto3.client('s3control')

def lambda_function(event, _=None):
  for record in event['Records']:
    bucket = record['s3']['bucket']['name']
    object_key = record['s3']['object']['key']

    response = s3control.create_job(
      AccountId=ACCOUNTID,
      ConfirmationRequired=False,
      Operation={
        'LambdaInvoke':{
          'FunctionArn': FUNCTION_ARN
        }
      },
      Report={
        'Bucket':REPORT_BUCKET_ARN,
        'Format':'CSV',
        'Enabled':True,
        'Prefix': 's3control/reports/%s/' % object_key
      },
      ClientRequestToken=object_key,
      Manifest={
        'Spec':{
          'Format':'S3BatchOperations_CSV_20180820',
          'Fields':[
            'Bucket',
            'Key'
          ]
        },
        'Location':{
          'ObjectArn': 'arn:aws:s3:::%s/%s' (bucket,object_key)
        }
      },
      Description= 'Automated skeletal extraction job',
      Priority=10,
      RoleArn= BATCH_ROLE_ARN
    )

  print(dumps(response, indent=2))