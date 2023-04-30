from os import environ

class Config:
  REGION_NAME = environ.get('AWS_REGION', 'us-east-2')
  DATA_BUCKET = environ.get('DATA_BUCKET', 'data.dissertation.natetorio.us')
  FETCH_QUEUE = environ.get('FETCH_QUEUE','https://sqs.us-east-2.amazonaws.com/995765563608/MovementExtractor-FetchQueue')
  STATUS_TABLE = environ.get('STATUS_TABLE','MovementExtractor_status-table')