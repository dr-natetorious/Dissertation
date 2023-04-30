import boto3
from typing import Tuple
from enum import Enum
from datetime import datetime
from time import mktime
from config import Config
from aws_xray_sdk.core import xray_recorder

ddb_client = boto3.client('dynamodb', region_name=Config.REGION_NAME)

class DownloadStatus(Enum):
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

  @xray_recorder.capture('write_stream_metadata')
  def write_stream_metadata(self,video_id:str,key:str,definition:dict):
    assert video_id is not None, "Missing video_id"
    assert key is not None, "Missing s3_key"
    assert definition is not None, "Missing definition"

    item = {
      'VideoId': { 'S': video_id },
      'SortKey': {'S': 'Stream::Format::%s' % key}
    }

    for key in definition.keys():
      value = definition[key]
      if isinstance(value, str):
        item[key] = {'S': value}
      elif isinstance(value,int):
        item[key]= {'N': str(value)}
      elif isinstance(value,dict):
        item[key] = {k: {'S':str(v)} for (k,v) in value.items()}

    ddb_client.put_item(
      TableName= Config.STATUS_TABLE,
      Item=item)

  @xray_recorder.capture('get_stream_status')
  def get_stream_status(self,video_id:str, key:str)->Tuple[DownloadStatus, datetime]:
    response = ddb_client.get_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': video_id},
        'SortKey': {'S': 'Stream::Status::%s' % key}
      },
      AttributesToGet=[
        'downloadStatus','lastUpdated'
      ])

    if not 'Item' in response:
      xray_recorder.put_annotation('stream_status','None')
      return (DownloadStatus.NONE, None)

    status = response['Item']['downloadStatus']['S']
    lastUpdated = response['Item']['lastUpdated']['N']
    
    xray_recorder.put_annotation('stream_status',status)
    xray_recorder.put_annotation('stream_lastUpdated',lastUpdated)
    return (DownloadStatus(status),datetime.fromtimestamp(float(lastUpdated)))

  @xray_recorder.capture('set_stream_status')
  def set_stream_status(self, video_id:str, key:str, status:DownloadStatus)->None:
    response = ddb_client.update_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': video_id},
        'SortKey': {'S': 'Stream::Status::%s' % key}
      },
      UpdateExpression="SET downloadStatus=:downloadStatus, lastUpdated=:lastUpdated",
      ExpressionAttributeValues={
        ':downloadStatus': {'S': status.value},
        ':lastUpdated': {'N': str(mktime(datetime.utcnow().timetuple())) }
      })    

  @xray_recorder.capture('get_video_status')
  def get_video_status(self,video_id:str)->Tuple[DownloadStatus, datetime]:
    response = ddb_client.get_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': video_id},
        'SortKey': {'S': 'File::Status'}
      },
      AttributesToGet=[
        'downloadStatus','lastUpdated'
      ])

    if not 'Item' in response:
      return (DownloadStatus.NONE, None)

    status = response['Item']['downloadStatus']['S']
    lastUpdated = response['Item']['lastUpdated']['N']
    return (DownloadStatus(status),datetime.fromtimestamp(float(lastUpdated)))

  @xray_recorder.capture('set_video_status')
  def set_video_status(self, video_id:str, status:DownloadStatus)->None:
    response = ddb_client.update_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': video_id},
        'SortKey': {'S': 'File::Status'}
      },
      UpdateExpression="SET downloadStatus=:downloadStatus, lastUpdated=:lastUpdated",
      ExpressionAttributeValues={
        ':downloadStatus': {'S': status.value},
        ':lastUpdated': {'N': str(mktime(datetime.utcnow().timetuple())) }
      })   
    