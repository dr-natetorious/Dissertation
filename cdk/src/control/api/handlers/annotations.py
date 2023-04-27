import boto3
from flask import Blueprint, request
from config import Config
from json import loads, dumps

annotations_api = Blueprint('annotations_api', __name__)

s3 = boto3.client('s3', region_name=Config.REGION_NAME)

@annotations_api.route('/annotations/list')
def list_labels():
  raise NotImplementedError()

@annotations_api.route('/annotations/of/<label>')
def list_videos_of_label(label:str):
  raise NotImplementedError()