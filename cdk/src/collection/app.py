#!/usr/bin/env python3
import boto3
from time import sleep
from signal import signal, SIGTERM
from config import Config
from handler import MessageHandler
from aws_xray_sdk.core import xray_recorder, patch_all

'''
Configure the clients
'''
sqs_client = boto3.client('sqs', region_name=Config.REGION_NAME)
message_handler = MessageHandler()

def shutdown(signnum, frame):
  print('Caught SIGTERM, exiting')
  exit(0)

def friendly_sleep(secs)->None:
  for _ in range(0,secs):
    sleep(1)

def configure_xray():
  xray_recorder.configure(
    service='YouTubeCollector',
    plugins=('EC2Plugin','ECSPlugin'),
    sampling=False
  )
  patch_all()
  

def main_loop():
  
  print('Monitoring Task Queue: %s' % Config.TASK_QUEUE_URL)
  print('Using Status Table   : %s' % Config.STATUS_TABLE)
  print('Persisting into      : s3://%s' % Config.DATA_BUCKET)

  while True:
    response = sqs_client.receive_message(
      QueueUrl=Config.TASK_QUEUE_URL,
      AttributeNames=['All'],
      MaxNumberOfMessages=1,
      VisibilityTimeout=300,
      WaitTimeSeconds=15)

    for message in response['Messages']:
      message_handler.process(message)

    friendly_sleep(Config.LOOP_SLEEP_SEC)

if __name__ == '__main__':
  configure_xray()
  xray_recorder.begin_segment('MainSegment')
  signal(SIGTERM, shutdown)
  main_loop()