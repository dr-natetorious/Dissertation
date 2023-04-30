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
  '''
  Represents the processing status of every video in the data set.
  '''
  @property
  def table_name(self)->str:
    '''
    Returns the name of the table.
    '''
    return self.__table_name

  def __init__(self, table_name:str) -> None:
    assert table_name is not None, "Missing table_name parameter"
    self.__table_name = table_name

  
  @xray_recorder.capture('get_extract_status')
  def get_extract_status(self,video_id:str)->Tuple[ExtractStatus, datetime]:
    '''
    Gets the extraction status for a specified video_id
    '''
    response = ddb_client.get_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': video_id},
        'SortKey': {'S': 'Extract::Status::v2' }
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

  @xray_recorder.capture('set_extract_status')
  def set_extract_status(self, video_id:str, status:ExtractStatus)->None:
    _ = ddb_client.update_item(
      TableName=Config.STATUS_TABLE,
      Key={
        'VideoId': {'S': video_id},
        'SortKey': {'S': 'Extract::Status::v2' }
      },
      UpdateExpression="SET extractStatus=:extractStatus, lastUpdated=:lastUpdated",
      ExpressionAttributeValues={
        ':extractStatus': {'S': status.value},
        ':lastUpdated': {'N': str(mktime(datetime.utcnow().timetuple())) }
      })
