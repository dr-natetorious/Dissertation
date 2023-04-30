import boto3
from flask import Blueprint, request
from config import Config
from json import loads, dumps

MAX_SQS_BATCH_SIZE = 10
SQS_QUEUE_URL = Config.OPENPOSE_QUEUE
people_api = Blueprint('people_api', __name__)

s3 = boto3.client('s3', region_name=Config.REGION_NAME)
rekognition = boto3.client('rekognition', region_name=Config.REGION_NAME)
sqs = boto3.client('sqs', region_name=Config.REGION_NAME)

@people_api.route('/people/process/<videoid>')
def start_processing_people(videoid:str):
    raise NotImplementedError()

@people_api.route('/people/start-tracking/<videoid>')
def list_people_tracking(videoid:str):
    return {
        'Video':{
            'VideoId': 12345,
            'Labels':['frame-labels']
        },
        'People':[
            {
                'Identity': {
                    'Alias': 'videoid-person-0x1234',
                },
                'Labels': [ 'detect-labels'],
                'NormalizedFrames': 's3://bucket/path/frames.tar.gz',
                'Debug':{
                    'Logs': 's3://bucket/path/prefix/files.txt',
                    'Frames': 's3://bucket/whatever/frames.tar.gz'
                } 
            }
        ]
    }

