from os import environ

class Config:
  REGION_NAME = environ.get('AWS_REGION', 'us-east-2')
  DATA_BUCKET = environ.get('DATA_BUCKET', 'data.dissertation.natetorio.us')