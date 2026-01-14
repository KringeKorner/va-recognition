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
C2C_MAX = 10
CONTROLLER_STOP = threading.Event()
CONTROLLER_THREAD = None

# queues
R2C = Queue(maxsize=2)
C2A = Queue(maxsize=2)
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
    print("CONTROLLER TERMINATED")

# main
# def main():
video_recorder.initialize(R2C)
while True:
    # if CONTROLLER_STOP.is_set():
    #     break
    print("RECEIVED FRAME")
    FRAME = R2C.get(timeout=0.5)
    cv.imshow("RECEIVING BAY", FRAME)
    if cv.waitKey(1) & 0xFF == ord("q"):
        video_recorder.clean_up()
        clean_up()
        break
