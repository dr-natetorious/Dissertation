import boto3
from json import loads
from os import environ

bucket_name = environ.get('BUCKET','data.dissertation.natetorio.us')
region_name = environ.get('REGION', environ.get('AWS_DEFAULT_REGION'))
s3 = boto3.client('s3', region_name=region_name)

def get_videoid(event:dict):
  if 'video_id' in event['arguments']:
    return event['arguments']['video_id']
  elif 'id' in event['source']:
    return event['source']['id']
  raise NotImplementedError('Unable to find videoid')

def lambda_function(event, context)->dict:
  print(event)

  video_id = get_videoid(event)

  response = s3.get_object(
    Bucket=bucket_name,
    Key='extract/%s/skeletons.json' % video_id)
  
  # items = list([{
  #   'id': video_id,
  # },
  # {
  #   'id': 'deadbeef',
  # }])
  items = list()

  json = loads(response['Body'].read())
  for action in json['Actions']:
    items.append({
      'id': '%s/%d'% (video_id, action['PersonId'])
    })

  return items

if __name__ == "__main__":
  lambda_function(
    event={
      'arguments':{},
      'source':{'id':'---0dWlqevI'}
    },
    context=None)