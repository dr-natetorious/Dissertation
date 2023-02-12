from typing import List
from pathlib import Path
from payload import Payload
from config import Config
import pyopenpose as op
import cv2

MILLISEC_PER_SEC = 1000

def create_params()->dict:
  params = {
    "model_folder": Config.MODEL_FOLDER,
    "face": True,
    "hand": True
  }
  return params
  

class SkeletonExtractor:

  @property
  def payload(self)->Payload:
    return self.__payload

  @payload.setter
  def payload(self,value)->None:
    self.__payload = value

  @property
  def local_file(self)->Path:
    return self.__local_file

  @payload.setter
  def local_file(self,value)->None:
    self.__local_file = value

  def __init__(self, payload:Payload, local_file:Path) -> None:
    self.payload = payload
    self.local_file = local_file

  def open(self):
    self.capture = cv2.VideoCapture(self.local_file)
    self.capture.set(cv2.CAP_PROP_POS_MSEC, int(self.payload.start_sec * MILLISEC_PER_SEC))

  def close(self):
    if self.capture is None:
      return

    self.capture.release()
    self.capture = None

  def frames(self, step_size_sec=0.5):
    results = []
    for offset in range(self.payload.start_sec, self.payload.end_sec, step_size_sec):
      _, frame = self.capture.set(cv2.CAP_PROP_POS_MSEC, int(offset * MILLISEC_PER_SEC))
      if frame == None:
        break
      results.append(frame)
    return results

  def process_frames(self):
    opWrapper = op.WrapperPython()
    opWrapper.configure(create_params())
    opWrapper.start()

    for frame in self.frames():
      datum = op.Datum()
      datum.cvInputData = frame
      opWrapper.emplaceAndPop([datum])
      body = datum.poseKeypoints
      print(str(body))
