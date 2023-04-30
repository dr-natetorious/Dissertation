from typing import List
from body import Body
# from PIL import Image

class Location:
  '''
  Represents where a frame is stored in Amazon S3
  '''
  def __init__(self, definition:dict) -> None:
    self.json = definition

  @property
  def input_frame_uri(self)->str:
    '''
    The URI of the input frame
    '''
    return self.json['input']

  @property
  def output_frame_uri(self)->str:
    '''
    The URI of the output frame
    '''
    return self.json['output']

class TarLocation(Location):
  '''
  Represents where a frame is stored in Amazon S3
  '''
  def __init__(self, definition:dict, tar_file:str) -> None:
    self.json = definition
    self.tar_file = tar_file
  

class Frame:
  '''
  Represents a single frame within a video
  '''
  def __init__(self, report, definition:dict) -> None:
    self.json = definition
    self.report = report
    self.__bodies = list()
    for ix in range(len(self.json['Bodies'])):
      self.__bodies.append(Body(self.json['Bodies'][ix],index=ix, frame_offset=self.offset_seconds))

  @property
  def offset_seconds(self)->float:
    '''
    The offset of the frame in seconds
    '''
    return self.json['Offset']

  @property
  def location(self)->Location:
    '''
    The location of the frame in Amazon S3
    '''
    if 'Location' in self.json:
      return Location(self.json['Location'])
    elif 'TarLocation' in self.json:
      return Location(self.json['TarLocation'])

  @property
  def bodies(self)->List[Body]:
    '''
    The bodies reported within this frame
    '''
    return self.__bodies

  @property
  def is_usable(self)->bool:
    '''
    Check if this frame has any usable information
    '''
    return len(self.bodies) > 0

  @property
  def error(self)->str:
    '''
    The error message reported by the service
    '''
    return self.json.get('Error',None)

  