from typing import Tuple
from enum import Enum
from datetime import datetime
from time import mktime
from config import Config
from aws import AWS
from aws_xray_sdk.core import xray_recorder


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
    response = AWS.ddb.get_item(
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
    response = AWS.ddb.update_item(
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
    