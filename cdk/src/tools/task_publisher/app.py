from os import path
import boto3
from json import loads, dumps

'''
Initialize constants
'''
REGION_NAME = 'us-east-2'
SQS_QUEUE_URL = 'https://sqs.us-east-2.amazonaws.com/995765563608/youtube-download-tasks'
GIT_ROOT = path.join(path.dirname(__file__),'..','..','..','..')
DATA_ROOT = path.join(GIT_ROOT,'kinetics','data','kinetics700_2020')
MAX_SQS_BATCH_SIZE = 10

sqs_client = boto3.client('sqs', region_name=REGION_NAME)

def get_json_file(name:str)->dict:
  file_name = path.join(DATA_ROOT,name+".json")
  with open(file_name,'rt') as f:
    json:dict = loads(f.read())
    for key in json.keys():
      if len(json[key]['annotations']['label']) == 0:
        json[key]['annotations']['label'] = 'test'
    return json

def display_error_response(response):
  failed = response['Failed']
  print('[ERROR] Failed to send %d messages due to %s' % (x
    len(failed),
    '; '.join(set([x['Message'] for x in failed]))))

def display_successful_response(response, total_successful)->int:
  successful = response['Successful']
  total_successful += len(successful)
  if total_successful % 1000 == 0:
    print("[INFO] Successfully sent %d total messages" % total_successful)
  return total_successful

def batch_send_dataset(name:str)->None:
  dataset = get_json_file(name)
  keys = list(dataset.keys())
  total_successful=0
  for ix in range(0,len(keys), MAX_SQS_BATCH_SIZE):
    batch = keys[ix:ix+MAX_SQS_BATCH_SIZE]

    response = sqs_client.send_message_batch(
      QueueUrl=SQS_QUEUE_URL,
      Entries=[
        {
          'Id': m,
          #'MessageDeduplicationId': m,
          #'MessageGroupId': dataset[m]['annotations']['label'],
          'MessageBody': dumps({
            'video_id':m,
            'properties': dataset[m]
          })
        } for m in batch
      ])

    if 'Failed' in response:
      display_error_response(response)
    if 'Successful' in response:
      total_successful = display_successful_response(response, total_successful)


if __name__ == "__main__":
  batch_send_dataset('test')
