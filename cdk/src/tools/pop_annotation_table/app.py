import boto3
from os import path
from json import loads, dumps

GIT_ROOT = path.join(path.dirname(__file__),'..','..','..','..')
DATA_ROOT = path.join(GIT_ROOT,'kinetics','data','kinetics700_2020')
TABLE_NAME = 'video-annotations'
MAX_BATCH_SIZE = 25

ddb = boto3.client('dynamodb', region_name='us-east-2')

def get_json_file(name:str)->dict:
  file_name = path.join(DATA_ROOT,name+".json")
  with open(file_name,'rt') as f:
    return loads(f.read())

def batch_send_dataset(name:str)->None:
  dataset = get_json_file(name)
  keys = list(dataset.keys())
  for ix in range(0,len(keys), MAX_BATCH_SIZE):
    batch = keys[ix:ix+MAX_BATCH_SIZE]
  
    items = list()
    for x in batch:
      items.append(
        {
          'VideoId': {'S': x},
          'label': {'S': dataset[x]['annotations']['label'] },
          'segment':{'NS':[str(x) for x in dataset[x]['annotations']['segment']] },
          'duration':{'N':str(dataset[x]['duration'])},
          'url':{'S':str(dataset[x]['url'])},
        })
      
    response = ddb.batch_write_item(
      RequestItems={
        TABLE_NAME:[
          {'PutRequest':{'Item': x }} for x in items
        ]
      })
    
    #print(response)

if __name__ == '__main__':
  batch_send_dataset('train')