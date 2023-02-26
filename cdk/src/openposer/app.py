#!/usr/bin/env python3
from time import sleep
from signal import signal, SIGTERM
from config import Config
from handler import MessageHandler
from aws import AWS
from concurrent.futures import ThreadPoolExecutor
from aws_xray_sdk.core import xray_recorder, patch_all

FIFTEEN_SEC = 15
SIXTY_SEC = 60
FIFTEEN_MIN = 15 * SIXTY_SEC
MAX_WORKERS = 1

pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)

def shutdown(signnum, frame):
  print('Caught SIGTERM, exiting')
  exit(0)

def configure_xray():
  xray_recorder.configure(
    service='OpenPoseAnalyzer',
    plugins=('EC2Plugin','ECSPlugin'),
    sampling=False
  )
  patch_all()
  

def main_loop():
  # print('Monitoring Task Queue: %s' % Config.TASK_QUEUE_URL)
  # print('Using Status Table   : %s' % Config.STATUS_TABLE)
  # print('Persisting into      : s3://%s' % Config.DATA_BUCKET)

  message_handler = MessageHandler()
  while True:
    xray_recorder.begin_segment('MainLoop')
    try:
      response = AWS.sqs.receive_message(
        QueueUrl=Config.TASK_QUEUE_URL,
        AttributeNames=['All'],
        MaxNumberOfMessages=1,
        VisibilityTimeout= FIFTEEN_MIN,
        WaitTimeSeconds=FIFTEEN_SEC)

      if not 'Messages' in response:
        continue

      for message in response['Messages']:
        message_handler.process(message)
    except Exception as error:
      print(str(error))
    finally:
      xray_recorder.end_segment()

if __name__ == '__main__':
  configure_xray()
  signal(SIGTERM, shutdown)
  for _ in range(0, MAX_WORKERS):
    pool.submit(main_loop)
  
  sleep(10)
  pool.shutdown(wait=True)