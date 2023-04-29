import boto3
from os import environ
from json import dumps

REGION_NAME = environ.get('REGION', environ.get('AWS_DEFAULT_REGION'))
BUCKET = environ.get('BUCKET', 'data.dissertation.natetorio.us')

s3 = boto3.client('s3', region_name=REGION_NAME)

def get_videoid(event:dict):
  if 'video_id' in event['arguments']:
    return event['arguments']['video_id']
  elif 'id' in event['source']:
    return event['source']['id']
  raise NotImplementedError('Unable to find videoid')

def lambda_function(event, context=None)->dict:
  print(event)

  video_id = get_videoid(event)
  prefix = 'video/%s' % video_id
  response = s3.list_objects(
    Bucket=BUCKET,
    Prefix= prefix
  )

  contents = response.get('Contents',list())
  cached = list()
  for obj in contents:
    object_key:str = obj['Key']

    if object_key.endswith('.json'):
      continue
    
    tags = s3.get_object_tagging(Bucket=BUCKET, Key=object_key).get('TagSet',[])
    properties = dict()
    for tag in tags:
      properties[tag['Key']] = tag['Value']
    
    properties['location']='s3://%s/%s' % (BUCKET,object_key)
    cached.append(properties)

  return cached

if __name__ == '__main__':
  response = lambda_function({
    'arguments':{},
    'source':{'id':'zzzzE0ncP1Y'}
  })

  print(dumps(response, indent=2))