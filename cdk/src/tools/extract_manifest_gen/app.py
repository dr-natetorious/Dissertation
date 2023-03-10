import boto3
from os import path, mkdir
from json import loads, dumps

GIT_ROOT = path.join(path.dirname(__file__),'..','..','..','..')
DATA_ROOT = path.join(GIT_ROOT,'kinetics','data','kinetics700_2020')
DATA_BUCKET_NAME = 'data.dissertation.natetorio.us'
MANIFEST_BUCKET_NAME = 'manifest.us-east-2.dissertation.natetorio.us'
REGION_NAME = 'us-east-2'
MANIFEST_ROOT = path.join(path.dirname(__file__),'manifest')
if not path.exists(MANIFEST_ROOT):
  mkdir(MANIFEST_ROOT)

s3 = boto3.client('s3', region_name=REGION_NAME)

def get_json_file(name:str)->dict:
  file_name = path.join(DATA_ROOT,name+".json")
  with open(file_name,'rt') as f:
    return loads(f.read())

def save_manifest(name:str, videos:list)->None:
  local_file = path.join(MANIFEST_ROOT, '%s.csv' % name.replace(" ","_"))

  manifest = map(lambda vid: '"%s","report/%s/%s.json"' % (
    DATA_BUCKET_NAME,
    name,
    vid
    ), videos)

  with open(local_file,'wt') as f:
    contents = '\n'.join(manifest)
    f.write(contents)

def upload_manifest(name:str, videos:list)->None:
  object_key = 'manifest/%s.csv' % name.replace(" ","_")

  s3.put_object(
    Bucket=MANIFEST_BUCKET_NAME,
    Key=object_key,
    Body='\n'.join([
      '%s,report/%s/%s.csv' % (
        MANIFEST_BUCKET_NAME,
        name,
        vid
      )
    ] for vid in videos)
  )

def generate_manfiests(name:str)->None:
  dataset = get_json_file(name)
  keys = list(dataset.keys())
  
  labels = dict()
  for video_id in keys:
    label = dataset[video_id]['annotations']['label']
    if label not in labels:
      labels[label] = list()
    labels[label].append(video_id)

  for label in labels.keys():
    save_manifest(label, labels[label])

if __name__ == '__main__':
  generate_manfiests('train')
