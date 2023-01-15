from cv2 import VideoCapture, CAP_PROP_POS_MSEC
from os import path

ROOT_FOLDER = path.dirname(__file__)

capture = VideoCapture(path.join(ROOT_FOLDER,'test2.mp4'))
capture.set(CAP_PROP_POS_MSEC, 1000)

result, frame = capture.read()

from PIL import Image
image = Image.fromarray(frame)
image.show()