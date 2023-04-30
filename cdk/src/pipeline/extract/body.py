from typing import List

class BodyPart:
  def __init__(self, position) -> None:
    self.x, self.y, self.confidence = position

class Body:
  def __init__(self, definition:List[list], index:int, frame_offset:int) -> None:
    self.json = definition
    self.index = index
    self.frame_offset = frame_offset
    # self.__high_confidence_only = self.drop_low_confidence()

  @property
  def frame_offset(self)->int:
    return self.__frame_offset
  
  @frame_offset.setter
  def frame_offset(self, value:int):
    self.__frame_offset = value

  @property
  def index(self)->int:
    return self.__index
  
  @index.setter
  def index(self, value:int):
    self.__index = value

  @property
  def body_parts(self)->List[BodyPart]:
    return [BodyPart(x) for x in self.json]

  @property
  def raw_array(self)->List[list]:
    return self.json

  # @property
  # def high_confidence_array(self)->List[list]:
  #   return self.__high_confidence_only
