# imports
import analyzer
import cv2 as cv
import debugger
from multiprocessing import Queue
import os
import time
import threading
import video_recorder
import queue

# vars
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEBUG_DIR = os.path.join(BASE_DIR, "DEBUG")
DEBUG_FILE = os.path.join(DEBUG_DIR, "DEBUGGER_OUT.txt")
C2C_MAX = video_recorder.FRAME_RATE
CONTROLLER_STOP = threading.Event()
CONTROLLER_THREAD = None

# queues
R2C = Queue(maxsize=1)
C2A = Queue(maxsize=1)
A2C = Queue(maxsize=1)
C2C = Queue(maxsize=C2C_MAX)

# helper functions
# def initialize():
#     global CONTROLLER_THREAD
#     print("INITIALIZING CONTROLLER")
#     CONTROLLER_THREAD = threading.Thread(target=main, args=(), daemon=False)
#     CONTROLLER_THREAD.start()

def clean_up():
    # CONTROLLER_STOP.set()
    # if CONTROLLER_THREAD is not None:
    #     print("STOPPING THREAD")
    #     # CONTROLLER_THREAD.join(timeout=2.0)
    #     print("THREAD ALIVE:", CONTROLLER_THREAD.is_alive())
    print("SHUTTING DOWN CONTROLLER")
    cv.destroyAllWindows()
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
    print("CONTROLLER TERMINATED")

def write_to_file(MESSAGE):
    with open(DEBUG_FILE, "a") as FILE:
        FILE.write(MESSAGE)

# main
# def main():

with open(DEBUG_FILE, "w") as FILE:
    FILE.write("")
video_recorder.initialize(R2C)
analyzer.initialize(C2A, A2C)
while True:
    # if CONTROLLER_STOP.is_set():
    #     break
    print("RECEIVED FRAME")
    FRAME = R2C.get(timeout=0.5)
    # cv.imshow("RECEIVING BAY", FRAME['FRAME'])
    print("SENDING FOR ANALYSIS")
    C2A.put(FRAME)
    print("RECEIVED RESULT")
    try:
        RESPONSE = A2C.get(timeout=0.5)
        if RESPONSE['FRAME']['FRAME'] is None:
            MESSAGE = f"RESULT IS: FRAME ID {RESPONSE['FRAME']['ID']}, {RESPONSE['LANDMARK']}, FRAME {RESPONSE['FRAME']['FRAME']}\n"
        else:
            MESSAGE = f"RESULT IS: FRAME ID {RESPONSE['FRAME']['ID']}, {RESPONSE['LANDMARK']}, FRAME PRESENT\n"
        write_to_file(MESSAGE)
    except queue.Empty:
        print("NONE")
    # if cv.waitKey(1) & 0xFF == ord("q"):
    if not RESPONSE['FRAME']['FRAME'] is None and RESPONSE['FRAME']['ID'] >= 300:
        video_recorder.clean_up()
        analyzer.clean_up(C2A)
        clean_up()
        break
