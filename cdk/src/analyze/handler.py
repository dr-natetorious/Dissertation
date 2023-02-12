import boto3
from tempfile import gettempdir
from pathlib import Path
from json import loads
from config import Config
from payload import Payload
from skeletal_extract import SkeletonExtractor
from status import StatusTable, AnalyzeStatus
from aws_xray_sdk.core import xray_recorder


temp_folder = Path(gettempdir())
status_table = StatusTable(Config.STATUS_TABLE)


class MessageHandler:
  def __init__(self) -> None:
    self.sqs_client = boto3.client('sqs', region_name=Config.REGION_NAME)
    self.s3_client = boto3.client('s3', region_name=Config.REGION_NAME)

  @xray_recorder.capture('process')
  def process(self,message:dict)->None:
    receipt_handle = message['ReceiptHandle']
    payload = Payload(message['Body'])
    _ = message['Attributes']

    status, lastUpdated = status_table.get_video_status(payload.video_id)
    xray_recorder.current_segment().put_annotation('video_id', payload.video_id)
    xray_recorder.current_segment().put_annotation('status', str(status.value))
    
    if status == AnalyzeStatus.COMPLETE:
      self.sqs_client.delete_message(
        QueueUrl=Config.TASK_QUEUE_URL,
        ReceiptHandle=receipt_handle)
      return
    
    local_file = self.download_file(payload)
    try:
      extractor = SkeletonExtractor(payload, local_file)
      extractor.open()
      extractor.process_frames()
      extractor.close()
    finally:
      local_file.unlink()

    self.sqs_client.delete_message(
        QueueUrl=Config.TASK_QUEUE_URL,
        ReceiptHandle=receipt_handle)
    return
    

  @xray_recorder.capture('download_file')
  def download_file(self, payload:Payload)->Path:
    local_path = temp_folder.joinpath(payload.video_id+".mp4")
    self.s3_client.download_file(
      payload.url.bucket,
      payload.url.object_key,
      str(local_path))
    return local_path
