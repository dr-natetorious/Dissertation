from os import environ

class Config:
  REGION_NAME = environ.get('AWS_REGION', 'us-east-2')
  DATA_BUCKET = environ.get('DATA_BUCKET', 'data.dissertation.natetorio.us')
  STATUS_TABLE = environ.get('STATUS_TABLE','rekon-status-table')
  MIN_CONFIDENCE = int(environ.get('MIN_CONFIDENCE', '70'))