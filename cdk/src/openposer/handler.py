from tempfile import gettempdir
from pathlib import Path
from json import loads, dumps
from config import Config
from payload import Payload
from aws import AWS
from uuid import uuid4
from skeletal_extract import SkeletonExtractor
from status import StatusTable, AnalyzeStatus
from aws_xray_sdk.core import xray_recorder


temp_folder = Path(gettempdir())
status_table = StatusTable(Config.STATUS_TABLE)


class MessageHandler:
  def __init__(self) -> None:
    return

  @xray_recorder.capture('process')
  def process(self,message:dict)->None:
    receipt_handle = message['ReceiptHandle']
    payload = Payload(message['Body'])
    _ = message['Attributes']

    status, lastUpdated = status_table.get_video_status(payload.video_id)
    xray_recorder.current_segment().put_annotation('video_id', payload.video_id)
    xray_recorder.current_segment().put_annotation('status', str(status.value))
    
    if payload.url.prefix is not None:
      if self.find_videos(payload) == False:
        AWS.sqs.delete_message(
          QueueUrl=Config.TASK_QUEUE_URL,
          ReceiptHandle=receipt_handle)
        return

    if status == AnalyzeStatus.COMPLETE:
      AWS.sqs.delete_message(
        QueueUrl=Config.TASK_QUEUE_URL,
        ReceiptHandle=receipt_handle)
      return
    
    local_file = self.download_file(payload)
    try:
      extractor = SkeletonExtractor(payload, local_file)
      extractor.open()
      report = extractor.process_frames()
      report.save()
      extractor.close()
    finally:
      local_file.unlink()

    status_table.set_video_status(payload.video_id, AnalyzeStatus.COMPLETE)
    AWS.sqs.delete_message(
        QueueUrl=Config.TASK_QUEUE_URL,
        ReceiptHandle=receipt_handle)

    return
    
  @xray_recorder.capture('find_videos')
  def find_videos(self, payload:Payload)->None:
    response = AWS.s3.list_objects_v2(
      Bucket = payload.url.bucket,
      Prefix= payload.url.prefix)
    
    mp4_file = [m['Key'] for m in response['Contents'] if m['Key'].endswith('.mp4')]
    if len(mp4_file) == 0:
      return False
    if len(mp4_file) == 1:
      payload.url.object_key = mp4_file[0]
      return True

    response = AWS.sqs.send_message_batch(
      QueueUrl=Config.TASK_QUEUE_URL,
      Entries=[
        {
          'Id': str(uuid4()),
          'MessageBody': dumps({
            'video_id': m['Key'],
            'properties': {
              's3uri':{
                'bucket': payload.url.bucket,
                'object_key': m['Key'],
              },
              'annotations': payload.json['properties']['annotations']
            }
          })
        } for m in response['Contents'] if m['Key'].endswith('.mp4')
      ])
    return False

  @xray_recorder.capture('download_file')
  def download_file(self, payload:Payload)->Path:
    local_path = temp_folder.joinpath(payload.video_id+".mp4")
    response = AWS.s3.get_object(
      Bucket=payload.url.bucket,
      Key=payload.url.object_key
    )

    with open(local_path,'wb') as f:
      f.write(response['Body'].read())

    return local_path
