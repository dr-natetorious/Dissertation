import boto3
from typing import List
from json import loads
from config import Config

s3 = boto3.client('s3', region_name=Config.REGION_NAME)

class IFrame:
  @property
  def offset(self)->float:
    raise NotImplementedError()
  
  @property
  def location(self)->dict:
    raise NotImplementedError()
  
  @property
  def source_uri(self)->str:
    raise NotImplementedError()
  
  @property
  def annotated_uri(self)->str:
    raise NotImplementedError()
  
  @property
  def has_error(self)->bool:
    raise NotImplementedError()
  
  @property
  def parent(self):
    raise NotImplementedError()

class IReport:
  @property
  def frame_bucket(self)->str:
    raise NotImplementedError()

  @property
  def frames(self)->List[IFrame]:
    raise NotImplementedError()
  
  @property
  def key_frames(self)->List[IFrame]:
    raise NotImplementedError()
  
  @property
  def parent(self):
    raise NotImplementedError()

class ISkeletonManifest:
  @property
  def video_id(self)->str:
    raise NotImplementedError()

  @property
  def report(self)->IReport:
    raise NotImplementedError()


class Frame:
  def __init__(self, parent:IReport, json:dict) -> None:
    self.__parent = parent
    self.json = json

  @property
  def parent(self)->IReport:
    return self.__parent

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
  def __init__(self, parent:ISkeletonManifest, bucket:str, object_key:str) -> None:
    self.__parent = parent
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
  def parent(self)->ISkeletonManifest:
    return self.__parent

  @property
  def frame_bucket(self)->str:
    return self.object['Bucket']

  @property
  def frames(self)->List[Frame]:
    return [Frame(self,x) for x in self.object['Frames']]
  
  @property
  def key_frames(self)->List[Frame]:
    return [
      x 
      for x in self.frames 
      if len(x.json['Bodies'])>0 and not x.has_error]

class SkeletonManifest(ISkeletonManifest):
  
  @property
  def video_id(self)->str:
    return self.object['VideoId']
  
  @property
  def report(self)->Report:
    if self.__report is None:
      report = self.object['Report']
      self.__report= Report(self, report['Bucket'], report['Key'])
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