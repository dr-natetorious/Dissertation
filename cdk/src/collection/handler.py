import boto3
import requests
from os import path
from subprocess import check_output
from tempfile import gettempdir
from config import Config
from json import loads, dumps

class Payload:
  def __init__(self, json) -> None:
    self.__raw = json
    self.__properties = loads(json)

    self.video_id = self.__properties['video_id']
    self.url = self.__properties['url']
    self.label = self.__properties['annotations']['label']

def make_template(video_id):
  template = '''
  {
      "context": {
          "client": {
              "hl": "en",
              "clientName": "WEB",
              "clientVersion": "2.20210721.00.00",
              "clientFormFactor": "UNKNOWN_FORM_FACTOR",
              "clientScreen": "WATCH",
              "mainAppWebInfo": {
                  "graftUrl": "/watch?v={{video_id}}",
              }
          },
          "user": {
              "lockedSafetyMode": False
          },
          "request": {
              "useSsl": True,
              "internalExperimentFlags": [],
              "consistencyTokenJars": []
          }
      },
      "videoId": "{{video_id}}",
      "playbackContext": {
          "contentPlaybackContext": {
              "vis": 0,
              "splay": False,
              "autoCaptionsDefaultOn": False,
              "autonavState": "STATE_NONE",
              "html5Preference": "HTML5_PREF_WANTS",
              "lactMilliseconds": "-1"
          }
      },
      "racyCheckOk": False,
      "contentCheckOk": False
  }
  '''.strip().format(video_id=video_id)
  return template

def make_command(local_file):
  command = '''curl "https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8" -H "Content-Type: application/json" --data "@%s"''' % local_file
  return command

class MessageHandler:
  '''
  Represents a utility for processing Amazon SQS messages.
  '''
  temp_folder = gettempdir()
  
  def __init__(self) -> None:
    self.sqs_client = boto3.client('sqs', region_name=Config.REGION_NAME)
    self.s3_client = boto3.client('s3', region_name=Config.REGION_NAME)
    self.ddb_client = boto3.client('dynamodb', region_name=Config.REGION_NAME)

  def process(self,message:dict)->None:
    receipt_handle = message['ReceiptHandle']
    payload = Payload(message['Body'])
    attributes = message['Attributes']

    json = self.get_video_info(payload.video_id)
    for format in json['streamingData']['formats']:
      itag = format['itag']
      url = format['url']
      remote_file = 'video/%s/%s.stream' % (payload.video_id,itag)
      self.fetch_file(payload.video_id, format,url,remote_file)

    self.sqs_client.delete_message(
      QueueUrl=Config.TASK_QUEUE_URL,
      ReceiptHandle=receipt_handle)

  def get_video_info(self,video_id):
    local_file = path.join(MessageHandler.temp_folder,'payload.json')
    with open(local_file, 'wt') as f:
      f.write(make_template(video_id))

    command = make_command(local_file)
    output = check_output(command)

    self.s3_client.put_object(
      Bucket=Config.DATA_BUCKET,
      Key='video/%s/get_info.json' % video_id,
      Body=output)

    json = loads(output)
    return json

  def fetch_file(self,video_id, definition, url, remote_file):
      download_stream = requests.get(url,stream=True)
      
      self.s3_client.put_object(
        Body=download_stream.content,
        Bucket=Config.DATA_BUCKET,
        Key=remote_file,
        ContentType=definition['mimeType'])

      self.s3_client.put_object(
        Body=dumps(definition,indent=2),
        Bucket=Config.DATA_BUCKET,
        Key='%s.manifest' % remote_file,
        ContentType='application/json')

      # Persist the format into DynamoDB
      item = {
        'VideoId': { 'S': video_id},
        'SortKey': {'S': 'Payload'}
      }

      for key in definition.keys():
        value = definition[key]
        if isinstance(value, str):
          item[key] = {'S': value}
        elif isinstance(value,int):
          item[key]= {'N': value}
        elif isinstance(value,dict):
          item[key] = {k: {'S':str(v)} for (k,v) in value.items()}

      self.ddb_client.put_item(
        TableName= Config.STATUS_TABLE,
        Item=item)
