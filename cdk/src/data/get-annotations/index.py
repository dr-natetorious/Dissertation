import boto3
from os import environ

table_name = environ.get('TABLE_NAME', 'video-annotations')
ddb = boto3.client('dynamodb')

def lambda_function(event, context)->dict:
  print(event)

  # response = ddb.get_item(
  #   TableName= table_name,
  #   Key={
  #     'VideoId': '---0dWlqevI'
  #   }
  # )

  return {
    'label':'test',
    'segment':{
      'start_sec': 10,
      'end_sec': 20
    }
  }

