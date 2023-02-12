from tempfile import gettempdir
from pathlib import Path
from json import loads
from config import Config
from payload import Payload
from aws import AWS
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
