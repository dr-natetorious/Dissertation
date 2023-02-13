import boto3
from io import BytesIO
from aws_xray_sdk.core import xray_recorder
from frame import Frame
from PIL import Image
from typing import List, Tuple
from json import loads
from config import Config

s3 = boto3.client('s3', region_name=Config.REGION_NAME)


class Report:
  def __init__(self, bucket:str, object_key:str) -> None:
    self.bucket = bucket
    self.object_key = object_key
    self.open()

  @xray_recorder.capture('Report::open')
  def open(self)->None:
    request = s3.get_object(Bucket=self.bucket, Key=self.object_key)
    self.json = loads(request['Body'].read())

    location = [f.location for f in self.frames if not f.location is None][0]
    request = s3.get_object(Bucket = self.bucket, Key=location.input_frame_uri)
    bytes = BytesIO(request['Body'].read())
    bytes.seek(0)

    self.image = Image.open(bytes)

  @property
  def image_size(self)->Tuple[int,int]:
    return self.image.size

  @property
  def bucket_name(self)->str:
    return self.json['Bucket']

  @property
  def video_id(self)->str:
    return self.json['VideoId']

  @property
  def frames(self)->List[Frame]:
    return [Frame(x) for x in self.json['Frames']]
