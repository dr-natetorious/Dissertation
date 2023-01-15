import requests

curl_command = '''
curl 'https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8' -H 'Content-Type: application/json' --data '{  "context": {    "client": {      "hl": "en",      "clientName": "WEB",      "clientVersion": "2.20210721.00.00",      "clientFormFactor": "UNKNOWN_FORM_FACTOR",   "clientScreen": "WATCH",      "mainAppWebInfo": {        "graftUrl": "/watch?v=UF8uR6Z6KLc",           }    },    "user": {      "lockedSafetyMode": false    },    "request": {      "useSsl": true,      "internalExperimentFlags": [],      "consistencyTokenJars": []    }  },  "videoId": "UF8uR6Z6KLc",  "playbackContext": {    "contentPlaybackContext": {        "vis": 0,      "splay": false,      "autoCaptionsDefaultOn": false,      "autonavState": "STATE_NONE",      "html5Preference": "HTML5_PREF_WANTS",      "lactMilliseconds": "-1"    }  },  "racyCheckOk": false,  "contentCheckOk": false}'
'''

headers = {
    'Content-Type': 'application/json'
}
data = {
    "context": {
        "client": {
            "hl": "en",
            "clientName": "WEB",
            "clientVersion": "2.20210721.00.00",
            "clientFormFactor": "UNKNOWN_FORM_FACTOR",
            "clientScreen": "WATCH",
            "mainAppWebInfo": {
                "graftUrl": "/watch?v=UF8uR6Z6KLc",
            }
        },
        "user": {
            "lockedSafetyMode": False
        },
        "request": {
            "useSsl": True,
            "internalExperimentFlags": [],
            "consistencyTokenJars": []
        }
    },
    "videoId": "UF8uR6Z6KLc",
    "playbackContext": {
        "contentPlaybackContext": {
            "vis": 0,
            "splay": False,
            "autoCaptionsDefaultOn": False,
            "autonavState": "STATE_NONE",
            "html5Preference": "HTML5_PREF_WANTS",
            "lactMilliseconds": "-1"
        }
    },
    "racyCheckOk": False,
    "contentCheckOk": False
}

url = 'https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8'


import subprocess
import os
payload = os.path.join(os.path.dirname(__file__),'payload.json')
command = '''curl "https://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8" -H "Content-Type: application/json" --data "@%s"''' % payload
res = subprocess.check_output(command)

from json import loads
response = loads(res)

video_id = 'UF8uR6Z6KLc' #response['responseContext']['playabilityStatus']['contextParams']
streams = response['streamingData']
for format in streams['formats']:
    itag = format['itag']
    url = format['url']
    local_file = str(itag)+'.mp4'
    outfile = os.path.join(os.path.dirname(__file__),'data','videos',video_id, local_file)
    if not os.path.exists(os.path.dirname(outfile)):
        os.mkdir(os.path.dirname(outfile))

    with open(outfile,'wb') as f:
        r = requests.get(url,stream=True)
        totalbits = 0
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                totalbits += 1024
                print("Downloaded",totalbits*1025,"KB...")
                f.write(chunk)

print(response)
print('done')

# seems to have some issue with ssl
#print('requesting...')
#r = requests.get('http://www.youtube.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8',headers=headers, json=data)
#print('received %s' % r.status_code)
#print(r.content)