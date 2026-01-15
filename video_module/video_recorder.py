# imports
from imutils.video import VideoStream as vs
import cv2 as cv
from multiprocessing import Queue
import os
import threading
import time
import queue

# vars
CAM_SRC = 0
CAM_RES = (720, 1280)
FRAME_RATE = 30
ID = 0
RECORDING_STOP = threading.Event()
RECORDER_THREAD = None
STREAM = None

# helper functions
def initialize(QUEUE):
    global STREAM, RECORDER_THREAD
    print("INITIALIZING RECORDING")
    STREAM = vs(src=CAM_SRC, resolution=CAM_RES, framerate=FRAME_RATE).start()
    time.sleep(2.0)
    RECORDER_THREAD = threading.Thread(target=main, args=(STREAM, QUEUE), daemon=True)
    RECORDER_THREAD.start()

def clean_up():
    print("STOPPING RECORDING")
    RECORDING_STOP.set()
    if STREAM is not None:
        print("STOPPING RECORDER")
        STREAM.stop()
        if hasattr(STREAM, "stream") and hasattr(STREAM.stream, "release"):
            STREAM.stream.release()
    if RECORDER_THREAD is not None:
        print("STOPPING THREAD")
        RECORDER_THREAD.join(timeout=2.0)
        print("THREAD ALIVE:", RECORDER_THREAD.is_alive())
    print("RECORDER TERMINATED")
    time.sleep(1.0)

# main
def main(STREAM, QUEUE):
    global ID
    if STREAM is None:
        print("INITIALIZATION REQUIRED")
    else:
        while True:
            if RECORDING_STOP.is_set():
                break
            FRAME = STREAM.read()
            if FRAME is None:
                continue
            try:
                ID += 1
                print("SENDING FRAME")
                FRAME_SENT = {
                    "ID": ID,
                    "FRAME": FRAME
                }
                QUEUE.put(FRAME_SENT, block=False)
            except queue.Full:
                print("FULL, SKIPPING FRAME")
                time.sleep(0.1)
