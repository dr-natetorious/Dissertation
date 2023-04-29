import boto3
from typing import List,Mapping
from os import environ
from json import loads, dumps

REGION_NAME = environ.get('REGION', environ.get('AWS_DEFAULT_REGION', 'us-east-2'))
ANNOTATION_TABLE= environ.get('ANNOTATION_TABLE', 'video-annotations')
BUCKET = environ.get('BUCKET', 'data.dissertation.natetorio.us')
CONFIDENCE_THRESHOLD = 0.7

BODY_PARTS = dict()
BODY_PARTS[0]=  "Nose"
BODY_PARTS[1]=  "Neck"
BODY_PARTS[2]= "RShoulder"
BODY_PARTS[3]= "RElbow"
BODY_PARTS[4]= "RWrist"
BODY_PARTS[5]= "LShoulder"
BODY_PARTS[6]= "LElbow"
BODY_PARTS[7]= "LWrist"
BODY_PARTS[8]= "MidHip"
BODY_PARTS[9]= "RHip"
BODY_PARTS[10]= "RKnee"
BODY_PARTS[11]="RAnkle"
BODY_PARTS[12]="LHip"
BODY_PARTS[13]="LKnee"
BODY_PARTS[14]="LAnkle"
BODY_PARTS[15]="REye"
BODY_PARTS[16]="LEye"
BODY_PARTS[17]="REar"
BODY_PARTS[18]="LEar"
BODY_PARTS[19]="LBigToe"
BODY_PARTS[20]="LSmallToe"
BODY_PARTS[21]="LHeel"
BODY_PARTS[22]="RBigToe"
BODY_PARTS[23]="RSmallToe"
BODY_PARTS[24]="RHeel"
BODY_PARTS[25]="Background"

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

  return object_key, loads(response)

def get_rekon_analysis(video_id:str)->dict:
  '''Fetch the Rekognition Analysis output for the target video'''
  object_key = 'rekognition/analyze/%s.json' % video_id
  response = s3.get_object(
    Bucket=BUCKET,
    Key=object_key
  )['Body'].read()

  return object_key, loads(response)

def get_extract_analysis(video_id:str)->dict:
  '''Fetch the MovemementTracker extraction output for the target video'''
  object_key = 'extract/%s/skeletons.json' % video_id
  response = s3.get_object(
    Bucket=BUCKET,
    Key=object_key
  )['Body'].read()

  return object_key, loads(response)

def lambda_function(event, context=None)->dict:
  print(event)

  video_id = get_videoid(event)
  op_object_key, op_analysis = get_openpose_analysis(video_id)
  extr_object_key, extract_analysis = get_extract_analysis(video_id)
  rek_object_key, rek_analysis = get_rekon_analysis(video_id)

  op_frames = dict()
  for x in op_analysis['Frames']:
    op_frames[x['Offset']]= x
  rek_frames = dict()
  for x in rek_analysis['KeyFrames']['Sampled']:
    rek_frames[x['Offset']]= x
  actions = dict()
  for action in extract_analysis['Actions']:
    offset = action['Metadata']['Frame']['Offset']
    if offset not in actions:
      actions[offset]=list()
    actions[offset].append(action)


  returned_frames = list()
  for offset in sorted(op_frames.keys()):
    op_f = op_frames[offset]
    frame = {
      'offset': op_f['Offset'],
      'location':{
        'sourceUri': op_f['Location']['input'],
        'skeletonUri': op_f['Location']['output'],
      },
      'bodies': render_bodies(op_f['Bodies'],offset,actions),
      'people_count': op_f['PeopleCount']
    }
    returned_frames.append(frame)

    if offset in rek_frames:
      rek_f = rek_frames[offset]
      frame['labels'] = [{
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
      for y in rek_f['Labels']]

  return {
    'manifest_files':{
      'openpose_analysis': op_object_key,
      'movement_analysis': extr_object_key,
      'rekon_analysis': rek_object_key
    },
    'frames': returned_frames
  }

def render_bodies(bodies:List[List[List[int]]], offset, actions:Mapping[float,List[dict]])->dict:
  '''Renders the Frame->body section'''
  results = list()
  for body_ix in range(len(bodies)):
    body = render_body_info(bodies[body_ix])
    results.append(body)
    if offset in actions:
      for action in actions[offset]:
        if action['Metadata']['BodyId']['Index'] == body_ix:
          body['identity'] = {
            'body_id': action['PersonId']
          }
          break
  return results

def render_body_info(body:List[List[int]])->dict:
  result = dict()
  #result['matrix']= body
  for ix in range(len(body)):
    x,y,c = body[ix]
    part:str = BODY_PARTS[ix]
    result[part.lower()]={
      'x': x,
      'y': y,
      'c': c,
      'visible': c > CONFIDENCE_THRESHOLD
    }
  return result

if __name__ == '__main__':
  response = lambda_function({
    'arguments':{},
    'source':{'id':'---0dWlqevI'}
  })

  print(dumps(response, indent=2))