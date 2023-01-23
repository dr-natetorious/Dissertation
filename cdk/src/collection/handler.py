import boto3
import requests
from os import path
from io import BytesIO
from datetime import datetime, timedelta
from status import StatusTable, DownloadStatus
from mimetypes import guess_extension
from subprocess import check_output
from tempfile import gettempdir
from config import Config
from json import loads, dumps

class Payload:
  def __init__(self, json) -> None:
    self.__raw = json
    self.__properties = loads(json)

    self.video_id = self.__properties['video_id']
    self.url = self.__properties['properties']['url']
    self.label = self.__properties['properties']['annotations']['label']

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
                  "graftUrl": "/watch?v=%s"
              }
          },
          "user": {
              "lockedSafetyMode": false
          },
          "request": {
              "useSsl": true,
              "internalExperimentFlags": [],
              "consistencyTokenJars": []
          }
      },
      "videoId": "%s",
      "playbackContext": {
          "contentPlaybackContext": {
              "vis": 0,
              "splay": false,
              "autoCaptionsDefaultOn": false,
              "autonavState": "STATE_NONE",
              "html5Preference": "HTML5_PREF_WANTS",
              "lactMilliseconds": "-1"
          }
      },
      "racyCheckOk": false,
      "contentCheckOk": false
  }
  '''.strip()
  template = template % (video_id,video_id)
  #template = dumps(loads(template),indent=2)
  return template

def make_command(local_file):
  #command = '''curl "https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8" -H "Content-Type: application/json" --data "@%s"''' % local_file
  command = ['curl',"https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8",
     '-H', "Content-Type: application/json",
     '--data', '@'+local_file
  ]
  return command

class MessageHandler:
  '''
  Represents a utility for processing Amazon SQS messages.
  '''
  temp_folder = gettempdir()
  
  def __init__(self) -> None:
    self.sqs_client = boto3.client('sqs', region_name=Config.REGION_NAME)
    self.s3_client = boto3.client('s3', region_name=Config.REGION_NAME)
    self.status_table = StatusTable(Config.STATUS_TABLE)

  def process(self,message:dict)->None:
    receipt_handle = message['ReceiptHandle']
    payload = Payload(message['Body'])
    _ = message['Attributes']

    status, _ = self.status_table.get_video_status(payload.video_id)
    if status == DownloadStatus.COMPLETE:
      self.sqs_client.delete_message(
        QueueUrl=Config.TASK_QUEUE_URL,
        ReceiptHandle=receipt_handle)
      return

    json = self.get_video_info(payload.video_id)
    for format in json['streamingData']['formats']:
      itag = format['itag']
      url = format['url']
      mimeType = format['mimeType']
      remote_file = 'video/%s/%s.%s' % (
        payload.video_id,
        itag,
        MessageHandler.extension(mimeType)
      )
      self.fetch_video_stream(payload.video_id, format,url,remote_file)

    self.status_table.set_video_status(payload.video_id, DownloadStatus.COMPLETE)
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

  @staticmethod
  def extension(mimeType:str)->str:
    type = guess_extension(mimeType)
    if not type is None:
      return type.lstrip('.')

    mimeType = mimeType.split(';')[0].strip()
    type = guess_extension(mimeType)
    if not type is None:
      return type.lstrip('.')

    mimeType = mimeType.split('/')[-1].strip()
    type = guess_extension(mimeType)
    if not type is None:
      return type.lstrip('.')

    if not mimeType is None:
      return mimeType

    return 'stream'

  def fetch_video_stream(self,video_id, definition, url, remote_file):
    '''
    Downloads the specified a video stream.
    '''
    # Check the download status.
    status,lastUpdated = self.status_table.get_stream_status(video_id,remote_file)
    if status == DownloadStatus.COMPLETE:
      return

    print('[FETCH VIDEO] video=%s to %s' % (video_id, remote_file))

    # if status == DownloadStatus.IN_PROGRESS:
    #   timeout = datetime.utcnow() + timedelta(days=1)
    #   if lastUpdated < timeout:
    #     return

    # Mark the download status...
    self.status_table.set_stream_status(video_id,remote_file, DownloadStatus.IN_PROGRESS)

    # Download the file
    self.__stream_to_s3(
      definition=definition,
      url=url,
      remote_file=remote_file)

    # Record the completion marker.
    self.status_table.write_stream_metadata(video_id,remote_file, definition)
    self.status_table.set_stream_status(video_id,remote_file, DownloadStatus.COMPLETE)

  def __stream_to_s3(self,definition, url, remote_file):  
      r = requests.get(url,stream=True)
      bytes = BytesIO()
      totalbits = 0
      for chunk in r.iter_content(chunk_size=1024):
        if chunk:
          totalbits += 1024
          if totalbits % (102400) == 0:
            print("Downloaded",totalbits*1025,"KB...")
          bytes.write(chunk)
      
      bytes.seek(0)

      self.s3_client.put_object(
        Body=bytes,
        Bucket=Config.DATA_BUCKET,
        Key=remote_file,
        ContentType=definition['mimeType'],
        Metadata={
          "itag":str(definition['itag']),
          "quality": definition['quality'] if 'quality' in definition else 'unknown'
        })

      # self.s3_client.put_object(
      #   Body=dumps(definition,indent=2),
      #   Bucket=Config.DATA_BUCKET,
      #   Key='%s.manifest' % remote_file,
      #   ContentType='application/json')
