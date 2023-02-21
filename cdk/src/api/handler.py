import boto3
import urllib
from os import environ, link
from json import dumps
from flask import request, redirect

def init_flask_for_env():
  """
  Loads flask for lambda or local debug.
  """
  from os import environ
  if 'LOCAL_DEBUG' in environ:
    from flask import Flask
    return Flask(__name__)
  else:
    from flask_lambda import FlaskLambda
    return FlaskLambda(__name__)

app = init_flask_for_env()

@app.route('/heartbeat')
def hello_world():
  return 'Hello, World!'

@app.route('/video/<id>')
def get_metadata(id:str):
  return {
    'VideoId': id,
    'Label': 'somelabel'
  }

@app.route('/youtube/<id>')
def get_youtube_metadata(id:str):
  return {
    'YouTube': id
  }

@app.route('/cached/<id>')
def get_collected_files(id:str):
  return  {
    'Collected':id
  }