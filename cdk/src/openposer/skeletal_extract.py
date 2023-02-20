from typing import List
from pathlib import Path
from payload import Payload
from config import Config
from report import Report
from aws_xray_sdk.core import xray_recorder
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

opWrapper = op.WrapperPython()
opWrapper.configure(create_params())
opWrapper.start()

class SkeletonExtractor:

  @property
  def payload(self)->Payload:
    return self.__payload

  @payload.setter
  def payload(self,value)->None:
    self.__payload = value

  @property
  def local_file(self)->str:
    return self.__local_file

  @local_file.setter
  def local_file(self,value)->None:
    self.__local_file = value

  def __init__(self, payload:Payload, local_file:Path) -> None:
    self.payload = payload
    self.local_file = str(local_file)

  def open(self):
    self.capture = cv2.VideoCapture(self.local_file)
    if not self.capture.isOpened():
      raise Exception('VideoCapture(%s) isOpen=%s' % (self.local_file, self.capture.isOpened()))
    return

  def close(self):
    if self.capture is None:
      return

    self.capture.release()
    self.capture = None

  def frames(self, step_size_sec=0.5):
    results = []
    offset = self.payload.start_sec
    while offset < self.payload.end_sec:
      self.capture.set(cv2.CAP_PROP_POS_MSEC, int(offset * MILLISEC_PER_SEC))
      
      _, frame = self.capture.read()
      if frame is None:
        break
      results.append((frame,offset))
      offset += step_size_sec
      
    return results

  @xray_recorder.capture('process_frames')
  def process_frames(self)->Report:
    report = Report(self.payload)
    for frame, offset in self.frames():
      datum = op.Datum()
      datum.cvInputData = frame
      opWrapper.emplaceAndPop([datum])
      report.add_frame_node(datum, offset)
    
    return report
