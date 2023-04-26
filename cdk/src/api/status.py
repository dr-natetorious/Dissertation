import boto3
from typing import Tuple
from enum import Enum
from datetime import datetime
from time import mktime
from config import Config
from aws_xray_sdk.core import xray_recorder

ddb_client = boto3.client('dynamodb', region_name=Config.REGION_NAME)

class ActionStatus(Enum):
  NONE='NONE',
  ERROR='ERROR'
  IN_PROGRESS='IN_PROGRESS'
  COMPLETE='COMPLETE'

class StatusTable:
  @property
  def table_name(self)->str:
    return self.__table_name

  def __init__(self, table_name:str) -> None:
    assert table_name is not None, "Missing table_name parameter"
    self.__table_name = table_name
  
  @xray_recorder.capture('get_process_status')
  def get_process_status(self,video_id:str)->Tuple[ActionStatus, datetime]:
    response = ddb_client.get_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': video_id},
        'SortKey': {'S': 'Rekognition::Process::Status' }
      },
      AttributesToGet=[
        'actionStatus','lastUpdated'
      ])

    if not 'Item' in response:
      xray_recorder.put_annotation('actionStatus','None')
      return (ActionStatus.NONE, None)

    status = response['Item']['actionStatus']['S']
    lastUpdated = response['Item']['lastUpdated']['N']
    
    xray_recorder.put_annotation('actionStatus',status)
    xray_recorder.put_annotation('actionLastUpdated',lastUpdated)
    return (ActionStatus(status),datetime.fromtimestamp(float(lastUpdated)))

  @xray_recorder.capture('set_process_status')
  def set_process_status(self, video_id:str, status:ActionStatus)->None:
    response = ddb_client.update_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': video_id},
        'SortKey': {'S': 'Rekognition::Process::Status' }
      },
      UpdateExpression="SET actionStatus=:actionStatus, lastUpdated=:lastUpdated",
      ExpressionAttributeValues={
        ':actionStatus': {'S': status.value},
        ':lastUpdated': {'N': str(mktime(datetime.utcnow().timetuple())) }
      })


  @xray_recorder.capture('get_process_frame_status')
  def get_frame_status(self,video_id:str, frame_uri:str)->Tuple[ActionStatus, datetime]:
    response = ddb_client.get_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': video_id},
        'SortKey': {'S': 'Rekognition::Process::Frame::%s' %frame_uri }
      },
      AttributesToGet=[
        'actionStatus','lastUpdated'
      ])

    if not 'Item' in response:
      xray_recorder.put_annotation('actionStatus','None')
      return (ActionStatus.NONE, None)

    status = response['Item']['actionStatus']['S']
    lastUpdated = response['Item']['lastUpdated']['N']
    
    xray_recorder.put_annotation('actionStatus',status)
    xray_recorder.put_annotation('actionLastUpdated',lastUpdated)
    return (ActionStatus(status),datetime.fromtimestamp(float(lastUpdated)))

  @xray_recorder.capture('set_process_status')
  def set_frame_status(self, video_id:str, frame_uri:str, status:ActionStatus)->None:
    response = ddb_client.update_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': video_id},
        'SortKey': {'S': 'Rekognition::Process::Frame::%s' %frame_uri }
      },
      UpdateExpression="SET actionStatus=:actionStatus, lastUpdated=:lastUpdated",
      ExpressionAttributeValues={
        ':actionStatus': {'S': status.value},
        ':lastUpdated': {'N': str(mktime(datetime.utcnow().timetuple())) }
      })

  @xray_recorder.capture('get_process_frame_status')
  def get_frame_face_status(self,video_id:str, frame_uri:str)->Tuple[ActionStatus, datetime]:
    response = ddb_client.get_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': video_id},
        'SortKey': {'S': 'Rekognition::Process::Face::%s' %frame_uri }
      },
      AttributesToGet=[
        'actionStatus','lastUpdated'
      ])

    if not 'Item' in response:
      xray_recorder.put_annotation('actionStatus','None')
      return (ActionStatus.NONE, None)

    status = response['Item']['actionStatus']['S']
    lastUpdated = response['Item']['lastUpdated']['N']
    
    xray_recorder.put_annotation('actionStatus',status)
    xray_recorder.put_annotation('actionLastUpdated',lastUpdated)
    return (ActionStatus(status),datetime.fromtimestamp(float(lastUpdated)))

  @xray_recorder.capture('set_process_status')
  def set_frame_face_status(self, video_id:str, frame_uri:str, status:ActionStatus)->None:
    response = ddb_client.update_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': video_id},
        'SortKey': {'S': 'Rekognition::Process::Face::%s' %frame_uri }
      },
      UpdateExpression="SET actionStatus=:actionStatus, lastUpdated=:lastUpdated",
      ExpressionAttributeValues={
        ':actionStatus': {'S': status.value},
        ':lastUpdated': {'N': str(mktime(datetime.utcnow().timetuple())) }
      })