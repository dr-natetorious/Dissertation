import boto3
from os import environ
from json import loads

REGION_NAME = environ.get('REGION', environ.get('AWS_DEFAULT_REGION'))
BUCKET = environ.get('BUCKET')

s3 = boto3.client('s3', region_name=REGION_NAME)

def get_videoid(event:dict):
  if 'video_id' in event['arguments']:
    return event['arguments']['video_id']
  elif 'id' in event['source']:
    return event['source']['id']
  raise NotImplementedError('Unable to find videoid')

def lambda_function(event, context)->dict:
  #print(event)

  video_id = get_videoid(event)
  object_key = 'video/%s/get_info.json' % video_id
  response = s3.get_object(
    Bucket=BUCKET,
    Key=object_key
  )

  json = loads(response['Body'].read())

  return {
    'id': video_id,
    'payload': 's3://%s/%s' % (BUCKET, object_key),
    'details': json['videoDetails'],
    'formats': [x for x in json['streamingData']['formats']]
  }
