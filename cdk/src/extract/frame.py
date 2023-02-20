from typing import List
from body import Body

class Location:
  def __init__(self, definition:dict) -> None:
    self.json = definition

  @property
  def input_frame_uri(self)->str:
    return self.json['input']

  @property
  def output_frame_uri(self)->str:
    return self.json['output']

class Frame:
  def __init__(self, definition:dict) -> None:
    self.json = definition

  @property
  def offset_seconds(self)->float:
    return self.json['Offset']

  @property
  def location(self)->Location:
    return Location(self.json['Location'])

  @property
  def bodies(self)->List[Body]:
    return [Body(x) for x in self.json['Bodies']]

  @property
  def is_usable(self)->bool:
    return len(self.bodies) > 0

  @property
  def error(self)->str:
    return self.json.get('Error',None)

  