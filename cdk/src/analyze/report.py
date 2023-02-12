import cv2
from io import BytesIO
from config import Config
from aws import AWS
from payload import Payload
from aws_xray_sdk.core import xray_recorder

class Report:

  @property
  def payload(self)->Payload:
    
    return self.__payload

  @payload.setter
  def payload(self,value)->None:
    self.__payload = value

  def __init__(self, payload:Payload) -> None:
    self.payload = payload
    self.document = dict()
    self.document['VideoId'] = payload.video_id
    self.document['Frames']= list()
    self.document['Bucket'] = Config.DATA_BUCKET

  def add_frame_node(self, datum, offset):
    frame = dict()
    bodies = datum.poseKeypoints
    frame["PeopleCount"] = len(bodies)
    frame["Offset"] = offset
    frame["Location"] = self.upload_frame_image(datum)
    frame["Bodies"] = list()    

    for ix in range(0,len(bodies)):
      frame["Bodies"].append(bodies[ix].tolist())

    self.document['Frames'].append(frame)
    return frame

  @xray_recorder.capture('save')
  def save(self)->None:
    AWS.s3.put_object(
      Bucket=Config.DATA_BUCKET,
      Key='report/%s/%s.json' %(
        self.payload.label,
        self.payload.video_id))

  @xray_recorder.capture('upload_frame_image')
  def upload_frame_image(self, datum)->None:
    input_frame = datum.cvInputData
    labeled_frame = datum.cvOutputData

    locations = {}
    for img, label in [(input_frame,'input'), (labeled_frame,'output')]:
      _, buffer = cv2.imencode('.jpg', img)
      buffer = BytesIO(buffer)
      buffer.seek(0)

      object_key = 'frames/%s/%s/%d.jpg' %(
        self.payload.video_id,
        label,
        len(self.document['Frames']))

      locations[label] = object_key

      AWS.s3.put_object(
        Body=buffer,
        Bucket=Config.DATA_BUCKET,
        Key = object_key
        )
    return locations