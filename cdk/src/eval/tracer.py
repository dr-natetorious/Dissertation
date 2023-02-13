import numpy as np
import boto3
from aws_xray_sdk.core import xray_recorder
from json import dumps
from config import Config
from report import Report
from typing import List, Tuple


MINIMUM_FRAMES = 3
s3 = boto3.client('s3', region_name=Config.REGION_NAME)

class MovementTracker:
  def __init__(self, report:Report) -> None:
    self.report = report
    self.image = report.image

  @xray_recorder.capture('MovementTracker::process_report')
  def process_report(self):
    people, metadata = self.extract_people()
    duplicates = MovementTracker.find_dups(people)
    
    unique_people=list()
    unique_meta = list()

    for ix in range(0,len(people)):
      if ix not in duplicates:
        unique_people.append(people[ix])
        unique_meta.append(metadata[ix])

    return unique_people, unique_meta

  @xray_recorder.capture('MovementTracker::save')
  def save(self)->None:
    people, metadata = self.process_report()
    object_key = 'extract/%s/skeletons.json' % (self.report.video_id)
    s3.put_object(
      Bucket = Config.DATA_BUCKET,
      Key=object_key,
      Body=dumps({
        'VideoId': self.report.video_id,
        'Report': {
          'Bucket': self.report.bucket_name,
          'Key': self.report.object_key,
        },
        'Actions': [{
          'PersonId': x,
          'Action': people[x],
          'Metadata': metadata[x]
          } 
          for x in range(0, len(people))
        ]
      })
    )

  @staticmethod
  def drop_low_conf(body, threshold=0.5):
      results =[]
      for x,y,c in body:
          if c < threshold:
              results.append([0,0,round(c,2)])
          else:
              results.append([int(x),int(y),round(c,2)])
      return results

  def norm_bodies(self, frame_id:int):
    bodies = [
      np.array(MovementTracker.drop_low_conf(b))* (1,1,0) / (self.image.size[0], self.image.size[1], 1) 
      for b in self.report.json['Frames'][frame_id]['Bodies']
    ]
    return bodies
  
  def total_frames(self):
    return len(self.report['Frames'])

  @staticmethod
  def closest_match(body, choices):
    best_dist = 99999
    match = None

    if choices is None:
        return None
    
    for choice in choices:
        dist = np.linalg.norm(body-choice)
        #print(dist)
        if dist < best_dist:
            best_dist = dist
            match = choice
    return match

  @xray_recorder.capture('MovementTracker::track_person')
  def track_person(self, frame_id, body):
    sequence = [body]
    if frame_id == self.total_frames():
        return None
    
    choices = self.norm_bodies(frame_id+1)
    best = MovementTracker.closest_match(body, choices)
    if best is None:
        return sequence
    
    sequence.extend(self.track_person(frame_id+1, best))
    return sequence

  @xray_recorder.capture('MovementTracker::extract_people')
  def extract_people(self)->Tuple[List[np.array],List[dict]]:
    people = []
    metadata =[]
    for f_ix in range(0,self.total_frames()):
        bodies = self.norm_bodies(f_ix)
        for b_ix in range(0,len(bodies)):
            body = bodies[b_ix]
            traced = self.track_person(f_ix+1, body)
            if len(traced) < MINIMUM_FRAMES:
                continue
            #print('Frame %d - %d - %d frames' %(f_ix, b_ix, len(traced)))
            people.append(np.array(traced))
            metadata.append({
              'Frame':{
                'Offset': self.report.frames[f_ix].offset_seconds,
                'Index': f_ix
              },
              'BodyId':{
                'Index': b_ix
              }
            })
    return people, metadata

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