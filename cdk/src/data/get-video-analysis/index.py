import boto3
from os import environ
from json import loads, dumps

REGION_NAME = environ.get('REGION', environ.get('AWS_DEFAULT_REGION'))
ANNOTATION_TABLE= environ.get('ANNOTATION_TABLE', 'video-annotations')
BUCKET = environ.get('BUCKET', 'data.dissertation.natetorio.us')

video_label_cache = dict()

s3 = boto3.client('s3', region_name=REGION_NAME)
ddb = boto3.client('dynamodb', region_name=REGION_NAME)

def get_videoid(event:dict):
  '''Get the VideoId from the inputMessage'''
  if 'video_id' in event['arguments']:
    return event['arguments']['video_id']
  elif 'id' in event['source']:
    return event['source']['id']
  raise NotImplementedError('Unable to find videoid')

def get_label(video_id:str)->str:
  '''Fetch the Video Label for the target video'''
  if video_id in video_label_cache:
    return video_label_cache[video_id]
  
  response = ddb.get_item(
    TableName= ANNOTATION_TABLE,
    Key={
      'VideoId': {'S': video_id}
    })

  label = response['Item']['label']['S']
  video_label_cache[video_id] = label
  return label

def get_openpose_analysis(video_id:str)->dict:
  '''Fetch the OpenPose output for the target video'''
  object_key = 'report/%s/%s.json' % (get_label(video_id), video_id)
  response = s3.get_object(
    Bucket=BUCKET,
    Key=object_key
  )['Body'].read()

  return loads(response)

def get_rekon_analysis(video_id:str)->dict:
  '''Fetch the Rekognition Analysis output for the target video'''
  object_key = 'rekognition/analyze/%s.json' % video_id
  response = s3.get_object(
    Bucket=BUCKET,
    Key=object_key
  )['Body'].read()

  return loads(response)

def lambda_function(event, context=None)->dict:
  print(event)

  video_id = get_videoid(event)
  object_key = 'rekognition/analyze/%s.json' % video_id
  response = s3.get_object(
    Bucket=BUCKET,
    Key=object_key
  )

  rek_analysis = loads(response['Body'].read())
  return {
    'manifest':{
      'location':'s3://%s/%s'%(rek_analysis['Manifest']['Bucket'], rek_analysis['Manifest']['Key']),
    },
    'frames':[
      {
        'offset': x['Offset'],
        'frame_location': {
          'sourceUri': x['Location']['SourceUri'],
          'skeletonUri': x['Location']['OpenPoseUri']
        },
        'labels':[
          {
            'name': y['Name'],
            'confidence': y['Confidence'],
            'instances': [{
              'confidence': z['Confidence'],
              'boundingBox': {
                'width': z['BoundingBox']['Width'],
                'height': z['BoundingBox']['Height'],
                'left': z['BoundingBox']['Left'],
                'top': z['BoundingBox']['Top']
              }
            } for z in y['Instances'] ],
            'parents': [{
              'name': z['Name'],
            } for z in y['Parents']],
            'aliases': [{
              'name': z['Name'] for z in y['Aliases']
            }],
            'categories':[{
              'name': z['Name'] 
            } for z in y['Categories']]
          }
          for y in x['Labels']
      ]
      }
    for x in rek_analysis['KeyFrames']['Sampled']]
  }

if __name__ == '__main__':
  response = lambda_function({
    'arguments':{},
    'source':{'id':'zzzzE0ncP1Y'}
  })

  print(dumps(response, indent=2))