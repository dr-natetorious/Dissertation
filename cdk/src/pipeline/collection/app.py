#!/usr/bin/env python3
import boto3
from time import sleep
from signal import signal, SIGTERM
from config import Config
from handler import MessageHandler
from concurrent.futures import ThreadPoolExecutor
from aws_xray_sdk.core import xray_recorder, patch_all

FIFTEEN_MIN = 60*15
FIFTEEN_SEC = 15
MAX_WORKERS = 4
MAX_MESSAGES= 10

'''
Configure the clients
'''
sqs_client = boto3.client('sqs', region_name=Config.REGION_NAME)
message_handler = MessageHandler()
pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)

def shutdown(signnum, frame):
  print('Caught SIGTERM, exiting')
  exit(0)

def configure_xray():
  xray_recorder.configure(
    service='YouTubeCollector',
    plugins=('EC2Plugin','ECSPlugin'),
    sampling=False
  )
  patch_all()
  

def main_loop():
  # print('Monitoring Task Queue: %s' % Config.TASK_QUEUE_URL)
  # print('Using Status Table   : %s' % Config.STATUS_TABLE)
  # print('Persisting into      : s3://%s' % Config.DATA_BUCKET)

  while True:
    xray_recorder.begin_segment('MainLoop')
    try:
      response = sqs_client.receive_message(
        QueueUrl=Config.TASK_QUEUE_URL,
        AttributeNames=['All'],
        MaxNumberOfMessages=MAX_MESSAGES,
        VisibilityTimeout= FIFTEEN_MIN,
        WaitTimeSeconds=FIFTEEN_SEC)

      for message in response['Messages']:
        message_handler.process(message)
    finally:
      xray_recorder.end_segment()

if __name__ == '__main__':
  configure_xray()
  signal(SIGTERM, shutdown)
  for _ in range(0, MAX_WORKERS):
    pool.submit(main_loop)

  pool.shutdown(wait=True)