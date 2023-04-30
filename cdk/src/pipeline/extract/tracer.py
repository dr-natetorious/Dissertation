import numpy as np
import boto3
from aws_xray_sdk.core import xray_recorder
from json import dumps
from body import Body
from config import Config
from report import Report
from typing import List, Tuple


MINIMUM_FRAMES = 3
FRAME_SAMPLE_RATE = 0.5
s3 = boto3.client('s3', region_name=Config.REGION_NAME)

class MovementTracker:
  '''
  Represents a utility for tracking movement in a video.
  '''
  def __init__(self, report:Report) -> None:
    self.report = report
    self.image = report.image

  @xray_recorder.capture('MovementTracker::process_report')
  def process_report(self):
    sequence = self.extract_people()
    min_sequences = MovementTracker.min_sequences(sequence)
    return min_sequences

  def min_sequences(sequences):
    '''
    Removes any duplicate paths from the dataset.
    '''
    sequence_encoding = dict()
    for s in sequences:
      encoding = ''
      for x in s['Sequence']:
        encoding += '[%s||%s]' % (x['FrameOffset'], x['BodyIndex'])
      sequence_encoding[encoding] = s
      
    duplicates = []
    keys = list(sequence_encoding.keys())
    for xi in range(len(sequence_encoding)-1,0,-1):
      for yi in range(0,len(sequence_encoding)):
        x = keys[xi]
        y = keys[yi]
        if x in y:
          duplicates.append(x)
    
    for dup in duplicates:
      del sequence_encoding[dup]
    
    return list(sequence_encoding.values())


  @xray_recorder.capture('MovementTracker::save')
  def save(self)->None:
    '''
    Persists the output into Amazon S3.
    '''
    sequence = self.process_report()
    object_key = 'movement/%s/analysis.json' % (self.report.video_id)
    s3.put_object(
      Bucket = Config.DATA_BUCKET,
      Key=object_key,
      Body=dumps({
        'Video':{
          'Id':self.report.video_id,
          'Width': self.image.width,
          'Height': self.image.height,
        },
        'Report': {
          'Bucket': self.report.bucket_name,
          'Key': self.report.object_key,
        },
        'Sequences': sequence,
      }))

  @staticmethod
  def drop_low_conf(body:Body, threshold=0.5):
    results =[]
    for x,y,c in body.raw_array:
        if c < threshold:
            results.append([0,0,round(c,2)])
        else:
            results.append([int(x),int(y),round(c,2)])
    return results

  def norm_bodies(self, frame_id:int):
    if frame_id >= self.total_frames():
       return None
    
    return self.report.frames[frame_id].bodies
  
  def total_frames(self):
    return len(self.report.frames)

  @staticmethod
  def closest_match(body:Body, choices:List[Body])->Body:
    best_dist = 99999
    match = None

    if choices is None:
        return None
    
    left = np.array(MovementTracker.drop_low_conf(body))* (1,1,0)
    for choice in choices:
        right = np.array(MovementTracker.drop_low_conf(choice))* (1,1,0)
        dist = np.linalg.norm(left-right)
        #print(dist)
        if dist < best_dist:
            best_dist = dist
            match = choice
    return match

  @xray_recorder.capture('MovementTracker::track_person')
  def track_person(self, frame_id:int, body:Body):
    sequence = [body]
    if frame_id == self.total_frames():
      return sequence
    
    choices = self.norm_bodies(frame_id+1)
    if choices is None:
      return sequence
    
    best = MovementTracker.closest_match(body, choices)
    if best is None:
      return sequence
    
    sequence.extend(self.track_person(frame_id+1, best))
    return sequence

  @xray_recorder.capture('MovementTracker::extract_people')
  def extract_people(self)->List[dict]: #Tuple[List[np.array],List[dict],List[dict]]:
    sequence = []
    for frame_id in range(0,self.total_frames()):
        for body in self.norm_bodies(frame_id):
            traced = self.track_person(frame_id+1, body)
            if len(traced) < MINIMUM_FRAMES:
                continue
            #print('Frame %d - %d - %d frames' %(f_ix, b_ix, len(traced)))
            # people.append(body)

            sequence.append({
               'Duration':{
                  'Start': self.report.frames[frame_id].offset_seconds,
                  'End': self.report.frames[frame_id].offset_seconds +len(traced)*FRAME_SAMPLE_RATE
               },
               'Sequence':[
                  {
                     'FrameOffset': x.frame_offset,
                     'BodyIndex': x.index,
                     'Body': x.json
                  } for x in traced
               ]
            })
    return sequence

  @staticmethod
  def are_equal(a, b):
    if a.shape != b.shape:
        return False
    for ai, bi in zip(a.flat, b.flat):
        if ai != bi:
            return False
    return True

  @staticmethod
  @xray_recorder.capture('MovementTracker::find_dups')
  def find_dups(people:List[np.array]):
    dups = []
    for ix in range(0,len(people)):
      if ix in dups:
          continue
          
      alice = people[ix]
      for f_ix in range(0, len(alice)):
        for iy in range(ix+1, len(people)):
          if iy in dups:
            break
              
          bob = people[iy]             
          for f_iy in range(0, len(bob)):
            dist = int(np.sum(people[ix][f_ix] - people[iy][f_iy]))
            if dist == 0:
              #print('match %d & %d' % (ix, iy))
              if len(alice) > len(bob):
                  dups.append(iy)
              else:
                  dups.append(ix)
              break
    return dups