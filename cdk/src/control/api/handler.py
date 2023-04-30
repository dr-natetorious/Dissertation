import boto3
import urllib
from json import dumps
from flask import request, redirect
from handlers.detection import detection_api
from handlers.youtube import youtube_api
from handlers.skeleton import skeleton_api
from handlers.identification import identification_api
from handlers.annotations import annotations_api

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
app.register_blueprint(detection_api)
app.register_blueprint(youtube_api)
app.register_blueprint(skeleton_api)
app.register_blueprint(identification_api)
app.register_blueprint(annotations_api)

@app.route('/heartbeat')
def hello_world():
  return 'Hello, World!'
