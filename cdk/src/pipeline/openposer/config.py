from os import environ

class Config:
  REGION_NAME = environ.get('REGION_NAME', 'us-east-2')
  TASK_QUEUE_URL = environ.get('TASK_QUEUE_URL','https://sqs.us-east-2.amazonaws.com/995765563608/openpose-tasks_gpu')
  STATUS_TABLE = environ.get('STATUS_TABLE', 'openpose-status')
  DATA_BUCKET = environ.get('DATA_BUCKET', 'data.dissertation.natetorio.us')
  MODEL_FOLDER = environ.get('MODEL_FOLDER', '/openpose/models')

  @staticmethod
  def validate():
    assert not Config.REGION_NAME is None, "Missing REGION_NAME"
    assert not Config.TASK_QUEUE_URL is None, "Missing TASK_QUEUE_URL"
    assert not Config.STATUS_TABLE is None, "Missing STATUS_TABLE"
    assert not Config.DATA_BUCKET is None, "Missing DATA_BUCKET"
    assert not Config.MODEL_FOLDER is None, "Missing MODEL_FOLDER"

Config.validate()    