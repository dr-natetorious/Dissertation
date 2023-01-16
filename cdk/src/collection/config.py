from os import environ

class Config:
  REGION_NAME = environ.get('REGION_NAME', 'us-east-2')
  TASK_QUEUE_URL = environ.get('TASK_QUEUE_URL')
  STATUS_TABLE = environ.get('STATUS_TABLE')
  DATA_BUCKET = environ.get('DATA_BUCKET')
  LOOP_SLEEP_SEC = int(environ.get('LOOP_SLEEP_SEC', 10))

  @staticmethod
  def validate():
    assert not Config.REGION_NAME is None, "Missing REGION_NAME"
    assert not Config.TASK_QUEUE_URL is None, "Missing TASK_QUEUE_URL"
    assert not Config.STATUS_TABLE is None, "Missing STATUS_TABLE"
    assert not Config.DATA_BUCKET is None, "Missing DATA_BUCKET"

Config.validate()    