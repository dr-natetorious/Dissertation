import boto3
from typing import List
from json import loads
from config import Config

s3 = boto3.client('s3', region_name=Config.REGION_NAME)

class Frame:
  def __init__(self, json:dict) -> None:
    self.json = json

  @property
  def offset(self)->float:
    return self.json['Offset']
  
  @property
  def location(self)->dict:
    return self.json['Location']
  
  @property
  def source_uri(self)->str:
    return self.location['input']
  
  @property
  def annotated_uri(self)->str:
    return self.location['output']
  
  @property
  def has_error(self)->bool:
    return 'Error' in self.json

class Report:
  def __init__(self, bucket:str, object_key:str) -> None:
    self.bucket = bucket
    self.object_key = object_key

    try:
      response = s3.get_object(
        Bucket=self.bucket,
        Key = self.object_key
      )
    except:
      self.object_key = self.object_key.replace('+',' ')
      response = s3.get_object(
        Bucket=self.bucket,
        Key = self.object_key
      )

    self.object = loads(response['Body'].read())

  @property
  def frame_bucket(self)->str:
    return self.object['Bucket']

  @property
  def frames(self)->List[Frame]:
    return [Frame(x) for x in self.object['Frames']]
  
  @property
  def key_frames(self)->List[Frame]:
    return [
      x 
      for x in self.frames 
      if len(x.json['Bodies'])>0 and not x.has_error]

class SkeletonManifest:
  
  @property
  def video_id(self)->str:
    return self.object['VideoId']
  
  @property
  def report(self)->Report:
    if self.__report is None:
      report = self.object['Report']
      self.__report= Report(report['Bucket'], report['Key'])
    return self.__report
  
  def __init__(self, bucket:str, object_key:str) -> None:
    self.bucket = bucket
    self.object_key = object_key
    self.__report = None

    response = s3.get_object(
      Bucket=self.bucket,
      Key=self.object_key
    )

    self.object = loads(response['Body'].read())