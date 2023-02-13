from typing import List
import numpy as np

class BodyPart:
  def __init__(self, position) -> None:
    self.x, self.y, self.confidence = position

class Body:
  def __init__(self, definition:List[list]) -> None:
    self.json = definition
    self.__high_confidence_only = self.drop_low_confidence()

  @property
  def body_parts(self)->List[BodyPart]:
    return [BodyPart(x) for x in self.json]

  @property
  def raw_array(self)->List[list]:
    return self.json

  @property
  def high_confidence_array(self)->List[list]:
    return self.__high_confidence_only

  # def drop_low_confidence(self, threshold:float=0.5):
  #   parts = []
  #   for part in self.body_parts:
  #     if part.confidence < threshold:
  #       parts.append([0,0,part.confidence])
  #     else:
  #       parts.append([part.x,part.y,part.confidence])
  #   return parts

  # @staticmethod
  # def take_positions(body:Body)->List[list]:
  #   return [[p.x,p.y] for p in body.body_parts]

  # @staticmethod
  # def distance(alice:Body, bob:Body):
  #   alice_position = alice.high_confidence_array * (1,1,0)
  #   bob_position = bob.high_confidence_array * (1,1,0)

  #   return np.abs(np.linalg.norm(alice_position,bob_position))

  # def closest_match(alice:Body, choices:List[Body])->Body:
  #   best_dist = 99999
  #   match = None

  #   for choice in choices:
  #     dist = Body.distance(alice,choice)
  #     if dist < best_dist:
  #       best_dist = dist
  #       match = choice
  #   return match

