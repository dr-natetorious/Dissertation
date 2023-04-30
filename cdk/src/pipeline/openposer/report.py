import cv2
import tarfile
from tempfile import gettempdir
from io import BytesIO
from os import unlink
from config import Config
from aws import AWS
from payload import Payload
from json import dumps
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

    self.tar_file_name = '%s/%s.tar.gz' %(gettempdir(),payload.video_id)
    self.tarfile = tarfile.open(self.tar_file_name,'w:gz')

    self.document['VideoId'] = payload.video_id
    self.document['Frames']= list()
    self.document['Bucket'] = Config.DATA_BUCKET
    self.document['TarFile'] = {
      'Bucket': Config.DATA_BUCKET,
      'Key': 'frames/tarfiles/%s/frames.tar.gz' % payload.video_id
    }

  def add_frame_node(self, datum, offset):
    frame = dict()
    self.document['Frames'].append(frame)
      

    frame["Offset"] = offset
    frame["TarLocation"] = self.attach_frame_images(datum)
    frame["Bodies"] = list()

    try:
      bodies = datum.poseKeypoints
      frame["PeopleCount"] = len(bodies)    
      for ix in range(0,len(bodies)):
        frame["Bodies"].append(bodies[ix].tolist())
    except Exception as error:
      frame['Error'] = str(error)
      print(str(error))
    
    return frame

  @xray_recorder.capture('save')
  def save(self)->None:

    '''
    Upload the tarfile
    '''
    self.tarfile.close()
    with open(self.tar_file_name,'rb') as f:
      AWS.s3.put_object(
        Bucket=Config.DATA_BUCKET,
        Key=self.document['TarFile']['Key'],
        Body = f.read(),
        Metadata={
          'VideoId': self.payload.video_id
        })
    unlink(self.tar_file_name)

    '''
    Upload the report
    '''
    AWS.s3.put_object(
      Bucket=Config.DATA_BUCKET,
      Body = dumps(self.document,indent=2),
      Metadata={
        'VideoId': self.payload.video_id
      },
      Key='report/%s/%s.json' %(
        self.payload.label,
        self.payload.video_id))

  @xray_recorder.capture('upload_frame_image')
  def attach_frame_images(self, datum)->None:
    input_frame = datum.cvInputData
    labeled_frame = datum.cvOutputData

    locations = {}
    for img, label in [(input_frame,'input'), (labeled_frame,'output')]:
      result, bytes = cv2.imencode('.jpg', img)

      object_key = 'frames/%s/%s/%d.jpg' %(
        self.payload.video_id,
        label,
        len(self.document['Frames']) -1)

      locations[label] = object_key

      tarinfo = tarfile.TarInfo(object_key)
      tarinfo.size = len(bytes)
      tarinfo.mode = 0o644

      self.tarfile.addfile(tarinfo, BytesIO(bytes))
      
    return locations

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
        len(self.document['Frames']) -1)

      locations[label] = object_key

      AWS.s3.put_object(
        Body=buffer,
        Bucket=Config.DATA_BUCKET,
        Key = object_key
        )
    return locations