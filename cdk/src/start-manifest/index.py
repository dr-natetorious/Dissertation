import boto3
from json import dumps
from os import environ

ACCOUNTID = environ.get('ACCOUNT_ID')
FUNCTION_ARN = environ.get('FUNCTION_ARN')
REPORT_BUCKET_ARN = environ.get('REPORT_BUCKET_ARN')
BATCH_ROLE_ARN = environ.get('BATCH_ROLE_ARN')

s3control = boto3.client('s3control')

def request(**kwargs):
  print(dumps(kwargs,indent=2))

def lambda_function(event, _=None):
  #print(event)
  for record in event['Records']:
    bucket = record['s3']['bucket']['name']
    object_key = record['s3']['object']['key']
    eTag = record['s3']['object']['eTag']

    response = s3control.create_job(
    #response = request(
      AccountId=ACCOUNTID,
      ConfirmationRequired=False,
      Operation={
        'LambdaInvoke':{
          'FunctionArn': FUNCTION_ARN
        }
      },
      Report={
        'Bucket':REPORT_BUCKET_ARN,
        'Format':'Report_CSV_20180820',
        'Enabled':True,
        'ReportScope':'FailedTasksOnly',
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
          'ObjectArn': 'arn:aws:s3:::%s/%s' % (bucket,object_key),
          'ETag': eTag,
        }
      },
      Description= 'Automated skeletal extraction job',
      Priority=10,
      RoleArn= BATCH_ROLE_ARN
    )

  print(dumps(response, indent=2))

if __name__ == '__main__':
  lambda_function(
    {'Records': [{'eventVersion': '2.1', 'eventSource': 'aws:s3', 'awsRegion': 'us-east-2', 'eventTime': '2023-02-20T12:39:13.893Z', 'eventName': 'ObjectCreated:Put', 'userIdentity': {'principalId': 'AWS:AIDA6PWCAWDMPAWA6K72G'}, 'requestParameters': {'sourceIPAddress': '72.17.34.35'}, 'responseElements': {'x-amz-request-id': 'BRW9RCS26YAMPCT9', 'x-amz-id-2': 'dya48PvhapJTI6TSV/NLNmiPIl6UianGLdvWA6rn12oWAifpxQc0otLIyddO6At8scZpBRhol/+jEIfEfD4zfhbozlD2uhig'}, 's3': {'s3SchemaVersion': '1.0', 'configurationId': 'Njg0MjU5ODgtNDE3ZS00NzI0LWI4ODEtM2JlNDdiNmFiZDU5', 'bucket': {'name': 'manifest.us-east-2.dissertation.natetorio.us', 'ownerIdentity': {'principalId': 'A2OB0MTZKAWAIP'}, 'arn': 'arn:aws:s3:::manifest.us-east-2.dissertation.natetorio.us'}, 'object': {'key': 'manifest/test/playing_accordion.csv', 'size': 88268, 'eTag': '55f257dd646f6929ceea0a2d449aca4c', 'sequencer': '0063F369F1ABD981ED'}}}]}
  )