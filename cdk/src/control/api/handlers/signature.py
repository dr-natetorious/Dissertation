import boto3
from flask import Blueprint, request
from config import Config
from json import loads, dumps

MAX_SQS_BATCH_SIZE = 10
SQS_QUEUE_URL = Config.OPENPOSE_QUEUE
signature_api = Blueprint('signature_api', __name__)

s3 = boto3.client('s3', region_name=Config.REGION_NAME)
rekognition = boto3.client('rekognition', region_name=Config.REGION_NAME)
sqs = boto3.client('sqs', region_name=Config.REGION_NAME)

@signature_api.route('/signature/start-tracking')
def start_movement_tracking():
    raise NotImplementedError()

@signature_api.route('/signature/get-tracking/<jobid>')
def get_movement_tracking(jobid:str):
    raise NotImplementedError()