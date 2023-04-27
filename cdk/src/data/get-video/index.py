import boto3
from os import environ

table_name = environ.get('BUCKET')
region_name = environ.get('REGION', environ.get('AWS_DEFAULT_REGION'))
ddb = boto3.client('dynamodb', region_name=region_name)

def get_videoid(event:dict):
  if 'video_id' in event['arguments']:
    return event['arguments']['video_id']
  elif 'id' in event['source']:
    return event['source']['id']
  raise NotImplementedError('Unable to find videoid')

def lambda_function(event, context)->dict:
  #print(event)

  video_id = get_videoid(event)

  # response = ddb.get_item(
  #   TableName= table_name,
  #   Key={
  #     'VideoId': {'S': video_id}
  #   })

  # item = response['Item']

  return {
    'id': video_id,
  }
