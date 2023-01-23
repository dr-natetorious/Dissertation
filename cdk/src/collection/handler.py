import boto3
from random import randint
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
from aws_xray_sdk.core import xray_recorder

GET_VIDEO_INFO_TIMEOUT_SEC= 30
DOWNLOAD_FILE_CHUNK_SIZE = 1024*1024*64

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

  @xray_recorder.capture('process')
  def process(self,message:dict)->None:
    receipt_handle = message['ReceiptHandle']
    payload = Payload(message['Body'])
    _ = message['Attributes']
    

    status, _ = self.status_table.get_video_status(payload.video_id)

    xray_recorder.current_segment().put_annotation('video_id', payload.video_id)
    xray_recorder.current_segment().put_annotation('status', str(status.value))

    if status in [DownloadStatus.COMPLETE, DownloadStatus.ERROR]:
      self.sqs_client.delete_message(
        QueueUrl=Config.TASK_QUEUE_URL,
        ReceiptHandle=receipt_handle)
      return

    try:
      json = self.get_video_info(payload.video_id)
    except Exception as e:
      xray_recorder.current_subsegment().add_exception(e)
      raise e

    if 'streamingData' not in json:
      xray_recorder.put_annotation('json',dumps(json,indent=2))
      self.status_table.set_video_status(payload.video_id, DownloadStatus.ERROR)
      self.sqs_client.delete_message(
        QueueUrl=Config.TASK_QUEUE_URL,
        ReceiptHandle=receipt_handle)
      return

    for format in MessageHandler.sort_formats(json['streamingData']['formats']):
      if 'url' not in format:
        continue

      #itag = format['itag'] if 'itag' in format else '0xdeadbeef'
      quality = format['quality'] if 'quality' in format else 'default'
      url = format['url']
      mimeType = format['mimeType'] if 'mimeType' in format else 'unknown'
      remote_file = 'video/%s/%s.%s' % (
        payload.video_id,
        quality,
        MessageHandler.extension(mimeType)
      )
      try:
        self.fetch_video_stream(payload.video_id, format,url,remote_file)
        break
      except Exception as e:
        self.status_table.set_stream_status(payload.video_id, remote_file, DownloadStatus.ERROR)

    self.status_table.set_video_status(payload.video_id, DownloadStatus.COMPLETE)
    self.sqs_client.delete_message(
      QueueUrl=Config.TASK_QUEUE_URL,
      ReceiptHandle=receipt_handle)

  @staticmethod
  def sort_formats(formats:list)->list:
    prefers = sorted(formats, key=lambda format: 4 if 'quality' not in format else 1 if format['quality'].startswith('hd') else 2 if format['quality'] == 'medium' else 3)
    #prefers = sorted(formats, lambda x: randint(1,10))
    return prefers

  @xray_recorder.capture('get_video_info')
  def get_video_info(self,video_id):
    local_file = path.join(MessageHandler.temp_folder,'payload.json')
    with open(local_file, 'wt') as f:
      f.write(make_template(video_id))

    command = make_command(local_file)
    output = check_output(command, timeout=GET_VIDEO_INFO_TIMEOUT_SEC)

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

  @xray_recorder.capture('fetch_video_stream')
  def fetch_video_stream(self,video_id, definition, url, remote_file):
    '''
    Downloads the specified a video stream.
    '''
    xray_recorder.current_subsegment().put_annotation('remote_file',remote_file)
    xray_recorder.current_subsegment().put_annotation('url',url)

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



  @xray_recorder.capture('stream_to_s3')
  def __stream_to_s3(self,definition, url, remote_file):  
      r = requests.get(url,stream=True)
      bytes = BytesIO()
      totalbits = 0
      trips =0
      for chunk in r.iter_content(chunk_size=DOWNLOAD_FILE_CHUNK_SIZE):
        trips +=1
        if chunk:
          totalbits += len(chunk)
          #if totalbits % (1024000) == 0:
          #  print("Downloaded",totalbits*1025,"KB...")
          bytes.write(chunk)
      
      xray_recorder.current_subsegment().put_annotation('total_bits', totalbits)
      xray_recorder.current_subsegment().put_annotation('total_trips', trips)
      bytes.seek(0)

      self.s3_client.put_object(
        Body=bytes,
        Bucket=Config.DATA_BUCKET,
        Key=remote_file,
        ContentType=definition['mimeType'],
        Metadata={
          #"itag":str(definition['itag']),
          "quality": definition['quality'] if 'quality' in definition else 'unknown'
        })
