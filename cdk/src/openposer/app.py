#!/usr/bin/env python3
from time import sleep
from signal import signal, SIGTERM
from config import Config
from handler import MessageHandler
from aws import AWS
from aws_xray_sdk.core import xray_recorder, patch_all

FIFTEEN_SEC = 15
SIXTY_SEC = 60
FIFTEEN_MIN = 15 * SIXTY_SEC

def shutdown(signnum, frame):
  print('Caught SIGTERM, exiting')
  exit(0)

def friendly_sleep(secs)->None:
  for _ in range(0,secs):
    sleep(1)

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
    finally:
      xray_recorder.end_segment()

    friendly_sleep(Config.LOOP_SLEEP_SEC)

if __name__ == '__main__':
  configure_xray()
  signal(SIGTERM, shutdown)
  main_loop()