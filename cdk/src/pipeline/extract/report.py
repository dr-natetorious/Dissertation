import boto3
from io import BytesIO
from aws_xray_sdk.core import xray_recorder
from frame import Frame
from PIL import Image
from typing import List, Tuple
from json import loads
from config import Config

s3 = boto3.client('s3', region_name=Config.REGION_NAME)

class NoFramesException(Exception):
  pass

class Report:
  '''
  Represents the output of the OpenPose GPU skeletal extraction.
  '''
  def __init__(self, bucket:str, object_key:str) -> None:
    self.bucket = bucket
    self.object_key = object_key
    self.open()

  @xray_recorder.capture('Report::open')
  def open(self)->None:
    print('GetObject(s3://%s/%s)' % (self.bucket,self.object_key))
    try:
      request = s3.get_object(Bucket=self.bucket, Key=self.object_key)
    except:
      request = s3.get_object(Bucket=self.bucket, Key=self.object_key.replace('+',' '))

    self.json = loads(request['Body'].read())
    self.frames = [Frame(self,x) for x in self.json['Frames']]

    # '''
    # Get the first frame location.        
    # '''
    # location = [f.location for f in self.frames if not f.location is None]
    # if len(location) == 0:
    #   raise NoFramesException()
    
    # location = location[0]
    # request = s3.get_object(Bucket = self.bucket, Key=location.input_frame_uri)
    # bytes = BytesIO(request['Body'].read())
    # bytes.seek(0)

    # self.image = Image.open(bytes)

  # @property
  # def image_size(self)->Tuple[int,int]:
  #   '''
  #   Returns the size of the image.    
  #   '''
  #   return self.image.size

  @property
  def bucket_name(self)->str:
    '''
    Returns the name of the bucket.
    '''    
    return self.json['Bucket']

  @property
  def video_id(self)->str:
    '''
    Returns the video id.
    '''
    return self.json['VideoId']

  @property
  def frames(self)->List[Frame]:
    '''
    Returns a list of frames.
    '''
    return self.__frames
  
  @frames.setter
  
  def frames(self,value:List[Frame])->None:
    '''
    Sets the frames.
    '''
    self.__frames = value
