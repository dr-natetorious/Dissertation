from json import loads

class S3Uri:
  @property
  def bucket(self)->str:
    return self.__bucket

  @property
  def object_key(self)->str:
    return self.__object_key
  
  @object_key.setter
  def object_key(self,value):
    self.__object_key =value
  
  @property
  def prefix(self)->str:
    return self.__prefix

  def __init__(self, uri:dict) -> None:
    self.__raw = uri
    self.__bucket = uri['bucket']
    self.__object_key = uri['object_key'] if 'object_key' in uri else None
    self.__prefix = uri['prefix'] if 'prefix' in uri else None

class Payload:
  @property
  def start_sec(self)->float:
    return self.__start_sec

  @start_sec.setter
  def start_sec(self, value)->None:
    self.__start_sec = value

  @property
  def end_sec(self)->float:
    return self.__end_sec

  @end_sec.setter
  def end_sec(self, value)->None:
    self.__end_sec = value

  def __init__(self, json) -> None:
    self.__raw = json
    self.json = loads(json)

    self.video_id:str = self.json['video_id']
    self.url = S3Uri(self.json['properties']['s3uri'])
    self.label:str = self.json['properties']['annotations']['label']
    self.start_sec, self.end_sec = self.json['properties']['annotations']['segment']