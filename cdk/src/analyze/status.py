import boto3
from typing import Tuple
from enum import Enum
from datetime import datetime
from time import mktime
from config import Config
from aws_xray_sdk.core import xray_recorder

ddb_client = boto3.client('dynamodb', region_name=Config.REGION_NAME)

class AnalyzeStatus(Enum):
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

  @xray_recorder.capture('get_video_status')
  def get_video_status(self,video_id:str)->Tuple[AnalyzeStatus, datetime]:
    response = ddb_client.get_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': 'Analyzer::%s' % video_id},
        'SortKey': {'S': 'File::Status'}
      },
      AttributesToGet=[
        'downloadStatus','lastUpdated'
      ])

    if not 'Item' in response:
      return (AnalyzeStatus.NONE, None)

    status = response['Item']['downloadStatus']['S']
    lastUpdated = response['Item']['lastUpdated']['N']
    return (AnalyzeStatus(status),datetime.fromtimestamp(float(lastUpdated)))

  @xray_recorder.capture('set_video_status')
  def set_video_status(self, video_id:str, status:AnalyzeStatus)->None:
    response = ddb_client.update_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': 'Analyzer::%s' % video_id},
        'SortKey': {'S': 'File::Status'}
      },
      UpdateExpression="SET downloadStatus=:downloadStatus, lastUpdated=:lastUpdated",
      ExpressionAttributeValues={
        ':downloadStatus': {'S': status.value},
        ':lastUpdated': {'N': str(mktime(datetime.utcnow().timetuple())) }
      })   
    