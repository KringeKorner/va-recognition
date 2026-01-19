# imports
from enum import Enum
from imutils.video import VideoStream as vs
import argparse
import cv2 as cv
from multiprocessing import Queue
import os
import threading
import time
import queue

# vars
ANALYZER_THREAD = None
ANALYSIS_STOP = threading.Event()
FRAME = None
LANDMARK_STATE = None

# classes
class LANDMARK(Enum):
    NO_LANDMARK = 1
    GENERAL_LANDMARK = 2
    KEY_LANDMARK = 3

# helper functions
def clean_up(RECV):
    ANALYSIS_STOP.set()
    if ANALYZER_THREAD is not None:
        print("SHUTTING DOWN ANALYZER")
        ANALYZER_THREAD.join(timeout=2.0)
        print("THREAD ALIVE:", ANALYZER_THREAD.is_alive())
    while not RECV.empty():
        try:
            _ = RECV.get_nowait()
        except queue.Empty:
            break
    print("ANALYZER TERMINATED")

def initialize(RECV, SEND, POC = False):
    global ANALYZER_THREAD, DETECTORS, FRAME
    print("INITIALIZING ANALYZER")
    ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
    AP = argparse.ArgumentParser()
    AP.add_argument("-c", "--cascades", type=str, default="cascades",
        help="path to input directory containing haar cascades")
    ARGS = vars(AP.parse_args())
    DETECTOR_PATHS = {
        "face": "haarcascade_frontalface_default.xml",
        "eyes": "haarcascade_eye.xml",
        "smile": "haarcascade_smile.xml",
    }
    print("LOADING HCC")
    DETECTORS = {}
    for (NAME, PATH) in DETECTOR_PATHS.items():
        PATH = os.path.join(ROOT_PATH, ARGS["cascades"], PATH)
        DETECTORS[NAME] = cv.CascadeClassifier(PATH)
    ANALYZER_THREAD = threading.Thread(target=main, args=(RECV, SEND, POC), daemon=False)
    ANALYZER_THREAD.start()
    time.sleep(2.0)

# main
def main(RECV, SEND, POC):
    if ANALYZER_THREAD is None:
        print("INITIALIZATION NEEDED")
    else:
        while not ANALYSIS_STOP.is_set():
            if ANALYSIS_STOP.is_set():
                break
            try:
                FRAME = RECV.get(timeout=0.5)
            except queue.Empty:
                continue
            if FRAME is None:
                continue
            FRAME_GRAY = cv.cvtColor(FRAME["FRAME"], cv.COLOR_BGR2GRAY)
            FACE_RECTS = DETECTORS["face"].detectMultiScale(
                FRAME_GRAY, scaleFactor=1.05, minNeighbors=5, minSize=(30, 30),
                flags=cv.CASCADE_SCALE_IMAGE)
            for (fX, fY, fW, fH) in FACE_RECTS:
                faceROI = FRAME_GRAY[fY:fY+ fH, fX:fX + fW]
                EYE_RECTS = DETECTORS["eyes"].detectMultiScale(
                    faceROI, scaleFactor=1.1, minNeighbors=10,
                    minSize=(15, 15), flags=cv.CASCADE_SCALE_IMAGE)
                SMILE_RECTS = DETECTORS["smile"].detectMultiScale(
                    faceROI, scaleFactor=1.1, minNeighbors=10,
                    minSize=(15, 15), flags=cv.CASCADE_SCALE_IMAGE)
            if not POC:
                if len(FACE_RECTS) > 0:
                    if len(EYE_RECTS) > 0 or len(SMILE_RECTS) > 0:
                        RESPONSE = {
                            "LANDMARK": LANDMARK(3),
                            "FRAME": FRAME
                        }
                    else:
                        RESPONSE = {
                            "LANDMARK": LANDMARK(2),
                            "FRAME": FRAME
                        }
                else:
                    RESPONSE = {
                        "LANDMARK": LANDMARK(1),
                        "FRAME": {
                            "ID": FRAME["ID"],
                            "FRAME": None
                        }
                    }
            else:
                print("TBD")
            try:
                SEND.put(RESPONSE)
            except queue.Full:
                continue
