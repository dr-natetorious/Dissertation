#!/usr/bin/python3
import boto3
from time import sleep
from signal import signal, SIGTERM
from config import Config
from handler import MessageHandler

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

def main_loop():
  while True:
    response = sqs_client.receive_message(
      QueueUrl=Config.TASK_QUEUE_URL,
      AttributeNames=['All'],
      MaxNumberOfMessages=1,
      VisibilityTimeout=60,
      WaitTimeSeconds=15)

    for message in response['Messages']:
      message_handler.process(message)

    friendly_sleep(Config.LOOP_SLEEP_SEC)

if __name__ == '__main__':
  signal(SIGTERM, shutdown)
  main_loop()