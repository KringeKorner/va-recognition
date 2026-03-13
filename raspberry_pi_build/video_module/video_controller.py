# imports
from queue import Queue
from video_module import analyzer
from video_module import debugger
from video_module import video_recorder
import cv2 as cv
import os
import time
import threading
import queue

# vars
ACTIVE = True
ANALYSIS_WINDOW = 1.0
ANALYSIS_CYCLE = 5.0
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUFFER = []
CONTROLLER_STOP = threading.Event()
CONTROLLER_THREAD = None
DEBUG_DIR = os.path.join(BASE_DIR, "DEBUG")
DEBUG_FILE = os.path.join(DEBUG_DIR, "VIDEO_CONTROLLER_LOG.txt")
FRAMES = []

# queues
R2C = Queue(maxsize=1)
C2A = Queue(maxsize=1)
A2C = Queue(maxsize=1)

# helper functions
def initialize(VC2C):
    global CONTROLLER_THREAD
    print("INITIALIZING VIDEO CONTROLLER")
    CONTROLLER_THREAD = threading.Thread(target=main, args=(VC2C,), daemon=False)
    CONTROLLER_THREAD.start()

def clean_up():
    CONTROLLER_STOP.set()
    video_recorder.clean_up()
    analyzer.clean_up(C2A)
    if CONTROLLER_THREAD is not None:
        print("STOPPING THREAD")
        CONTROLLER_THREAD.join(timeout=2.0)
        print("THREAD ALIVE:", CONTROLLER_THREAD.is_alive())
    print("SHUTTING DOWN VIDEO CONTROLLER")
    while not R2C.empty():
        try:
            _ = R2C.get_nowait()
        except queue.Empty:
            break
    while not A2C.empty():
        try:
            _ = A2C.get_nowait()
        except queue.Empty:
            break
    print("VIDEO CONTROLLER TERMINATED")

def write_to_file(MESSAGE):
    with open(DEBUG_FILE, "a") as FILE:
        FILE.write(MESSAGE)

# main
def main(VC2C):
    global ACTIVE
    with open(DEBUG_FILE, "w") as FILE:
        FILE.write("")
    video_recorder.initialize(R2C)
    analyzer.initialize(C2A, A2C)
    CYCLE_START = time.monotonic()
    while True:
        ANALYSIS_START = time.monotonic()
        elapsed = ANALYSIS_START - CYCLE_START
        if elapsed >= ANALYSIS_CYCLE:
            CYCLE_START = ANALYSIS_START
            BUFFER.clear()
            ACTIVE = True
        elif elapsed >= ANALYSIS_WINDOW:
            ACTIVE = False
        if CONTROLLER_STOP.is_set():
            break
        try:
            FRAME = R2C.get(timeout=0.2)
        except queue.Empty:
            continue
        try:
            C2A.put(FRAME, timeout=0.2)
        except queue.Full:
            continue
        if ACTIVE:
            try:
                RESPONSE = A2C.get(timeout=0.2)
                if RESPONSE['FRAME']['FRAME'] is None:
                    MESSAGE = f"RESULT IS: FRAME ID {RESPONSE['FRAME']['ID']}, {RESPONSE['LANDMARK']}, FRAME {RESPONSE['FRAME']['FRAME']}\n"
                else:
                    MESSAGE = f"RESULT IS: FRAME ID {RESPONSE['FRAME']['ID']}, {RESPONSE['LANDMARK']}, FRAME PRESENT\n"
                    BUFFER.append(RESPONSE)
                write_to_file(MESSAGE)
            except queue.Empty:
                continue
        elif not ACTIVE:
            if not CONTROLLER_STOP.is_set():
                try:
                    if len(BUFFER) == 0:
                            VC2C.put({
                            "BUFFER": None,
                            "SOURCE": 1,
                            "TIMESTAMP": CYCLE_START,
                        }, block=False)
                    else: 
                        VC2C.put({
                            "BUFFER": BUFFER.copy(),
                            "SOURCE": 1,
                            "TIMESTAMP": CYCLE_START,
                        }, block=False)
                except queue.Full:
                    pass
            BUFFER.clear()
