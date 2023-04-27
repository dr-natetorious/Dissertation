import boto3
from typing import Tuple
from enum import Enum
from datetime import datetime
from time import mktime
from config import Config
from aws_xray_sdk.core import xray_recorder

ddb_client = boto3.client('dynamodb', region_name=Config.REGION_NAME)

class ExtractStatus(Enum):
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

  
  @xray_recorder.capture('get_extract_status')
  def get_extract_status(self,video_id:str)->Tuple[ExtractStatus, datetime]:
    response = ddb_client.get_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': video_id},
        'SortKey': {'S': 'Extract::Status' }
      },
      AttributesToGet=[
        'extractStatus','lastUpdated'
      ])

    if not 'Item' in response:
      xray_recorder.put_annotation('extractStatus','None')
      return (ExtractStatus.NONE, None)

    status = response['Item']['extractStatus']['S']
    lastUpdated = response['Item']['lastUpdated']['N']
    
    xray_recorder.put_annotation('extractStatus',status)
    xray_recorder.put_annotation('extractLastUpdated',lastUpdated)
    return (ExtractStatus(status),datetime.fromtimestamp(float(lastUpdated)))

  @xray_recorder.capture('set_extractStatus')
  def set_extract_status(self, video_id:str, status:ExtractStatus)->None:
    response = ddb_client.update_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': video_id},
        'SortKey': {'S': 'Extract::Status'}
      },
      UpdateExpression="SET extractStatus=:extractStatus, lastUpdated=:lastUpdated",
      ExpressionAttributeValues={
        ':extractStatus': {'S': status.value},
        ':lastUpdated': {'N': str(mktime(datetime.utcnow().timetuple())) }
      })
