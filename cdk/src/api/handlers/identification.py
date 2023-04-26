import boto3
from flask import Blueprint, request
from config import Config
from json import loads, dumps
from status import StatusTable, ActionStatus

MAX_SQS_BATCH_SIZE = 10
SQS_QUEUE_URL = Config.OPENPOSE_QUEUE
identification_api = Blueprint('identification_api', __name__)

s3 = boto3.client('s3', region_name=Config.REGION_NAME)
rekognition = boto3.client('rekognition', region_name=Config.REGION_NAME)
sqs = boto3.client('sqs', region_name=Config.REGION_NAME)

@identification_api.route('/identification/<videoid>')
def start_identification(videoid:str):
    raise NotImplementedError()