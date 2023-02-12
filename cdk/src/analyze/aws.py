import boto3
from config import Config

class AWS:
  s3 = boto3.client('s3', region_name=Config.REGION_NAME)
  sqs = boto3.client('sqs', region_name=Config.REGION_NAME)
  ddb = boto3.client('dynamodb', region_name=Config.REGION_NAME)