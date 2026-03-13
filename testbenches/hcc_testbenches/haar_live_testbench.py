from imutils.video import VideoStream as vs
import argparse
import imutils
import time
import cv2
import os
from pynput import keyboard

# Haar cascades URL: https://github.com/opencv/opencv/tree/3.4/data/haarcascades

# vars
CAM_SRC = 0
# CAM_RES = (640, 480)
CAM_RES = (1280, 720)
FRAME_RATE = 30

# extracting root path
root_path = os.path.dirname(os.path.abspath(__file__))
print(root_path)
# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--cascades", type=str, default="cascades",
	help="path to input directory containing haar cascades")
args = vars(ap.parse_args())
# initialize a dictionary that maps the name of the haar cascades to
# their filenames
detectorPaths = {
	"face": "haarcascade_frontalface_default.xml",
	"eyes": "haarcascade_eye.xml",
	"smile": "haarcascade_smile.xml",
}
# initialize a dictionary to store our haar cascade detectors
print("[INFO] loading haar cascades...")
detectors = {}
# loop over our detector paths
for (name, path) in detectorPaths.items():
	# load the haar cascade from disk and store it in the detectors
	# dictionary
	path = os.path.join(root_path, args["cascades"], path)
	detectors[name] = cv2.CascadeClassifier(path)
# initialize the video stream and allow the camera sensor to warm up
print("[INFO] starting video stream...")
STREAM = vs(src=CAM_SRC, resolution=CAM_RES, framerate=FRAME_RATE).start()
time.sleep(2.0)
# loop over the frames from the video stream
while True:
	# grab the frame from the video stream, resize it, and convert it
	# to grayscale
	frame = STREAM.read()
	frame = imutils.resize(frame, width=500)
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	# perform face detection using the appropriate haar cascade
	faceRects = detectors["face"].detectMultiScale(
		gray, scaleFactor=1.05, minNeighbors=5, minSize=(30, 30),
		flags=cv2.CASCADE_SCALE_IMAGE)
	# loop over the face bounding boxes
	for (fX, fY, fW, fH) in faceRects:
		# extract the face ROI
		faceROI = gray[fY:fY+ fH, fX:fX + fW]
		# apply eyes detection to the face ROI
		eyeRects = detectors["eyes"].detectMultiScale(
			faceROI, scaleFactor=1.1, minNeighbors=10,
			minSize=(15, 15), flags=cv2.CASCADE_SCALE_IMAGE)
		# apply smile detection to the face ROI
		smileRects = detectors["smile"].detectMultiScale(
			faceROI, scaleFactor=1.1, minNeighbors=10,
			minSize=(15, 15), flags=cv2.CASCADE_SCALE_IMAGE)
		# loop over the eye bounding boxes
		for (eX, eY, eW, eH) in eyeRects:
			# draw the eye bounding box
			ptA = (fX + eX, fY + eY)
			ptB = (fX + eX + eW, fY + eY + eH)
			cv2.rectangle(frame, ptA, ptB, (0, 0, 255), 2)
		# loop over the smile bounding boxes
		for (sX, sY, sW, sH) in smileRects:
			# draw the smile bounding box
			ptA = (fX + sX, fY + sY)
			ptB = (fX + sX + sW, fY + sY + sH)
			cv2.rectangle(frame, ptA, ptB, (255, 0, 0), 2)
		# draw the face bounding box on the frame
		cv2.rectangle(frame, (fX, fY), (fX + fW, fY + fH),
			(0, 255, 0), 2)
	# show the output frame
	cv2.imshow("Frame", frame)
	key = cv2.waitKey(1) & 0xFF
	# if the `q` key was pressed, break from the loop
	if key == ord("q"):
		break
# do a bit of cleanup
cv2.destroyAllWindows()
vs.stop()