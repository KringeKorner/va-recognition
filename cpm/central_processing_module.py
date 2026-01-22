# imports
from enum import Enum
from pathlib import Path
from vai.CANDIDATE_1.Deepface import VAI
from video_module import controller
from queue import Queue
import cv2 as cv
import keyboard
import multiprocessing
from pathlib import Path
import time
import threading
import queue
# vars
BATCH_ID = 0
CPM_HALT = threading.Event()
C2C_MAX = 30
FRAMES = []
VAI_HALT = multiprocessing.Event()
VAI_READY = multiprocessing.Event()
ROOT_PATH = Path(__file__).resolve().parent
DEBUG_PATH = Path(ROOT_PATH).parent / 'video_module' / 'DEBUG'
CPM_LOGGER_PATH = Path(DEBUG_PATH) / 'CPM_LOGGER.txt'

# queues
C2C = Queue(maxsize=1)
C2V = multiprocessing.Queue(maxsize=1)
V2C = multiprocessing.Queue(maxsize=1)

# classes
class SOURCE(Enum):
    VIDEO = 1
    AUDIO = 2

# helper functions
def clean_up():
    print("SHUTTING DOWN CPM")
    VAI.clean_up(C2V, VAI_HALT)
    controller.clean_up()
    while not C2C.empty():
        try:
            _ = C2C.get_nowait()
        except queue.Empty:
            break
    while not V2C.empty():
        try:
            _ = V2C.get_nowait()
        except queue.Empty:
            break
    print("CPM TERMINATED")

def write_to_file(MESSAGE):
    with open(CPM_LOGGER_PATH, "a") as FILE:
        FILE.write(MESSAGE)

# main
def main():
    global BATCH_ID
    with open(CPM_LOGGER_PATH, "w") as FILE:
        FILE.write("")
    VAI.initialize(C2V, V2C, VAI_HALT, VAI_READY)
    VAI_READY.wait()
    controller.initialize(C2C)
    try:
        while not CPM_HALT.is_set():
            if keyboard.is_pressed('q'):
                CPM_HALT.set()
                clean_up()
                break
            try:
                BATCH_ID += 1
                PACKET = C2C.get(timeout=1/C2C_MAX)
                BUFFER_SOURCE = SOURCE(PACKET['SOURCE'])
                FRAME_QNT = len(PACKET['BUFFER'])
                for RESPONSE in PACKET['BUFFER']:
                    FRAMES.append(RESPONSE['FRAME']['FRAME'])
                print(f"Received packet from: {BUFFER_SOURCE} of size {FRAME_QNT}")
                try:
                    print(f"Sending {len(FRAMES)} to VAI")
                    C2V.put(FRAMES.copy(), block=False)
                except multiprocessing.queues.Full:
                    continue
                FRAMES.clear()
                try:
                    RESULT = V2C.get(timeout=1/FRAME_QNT)
                    EMOTION = RESULT['EMOTION']
                    AVG_CONFIDENCE = RESULT['AVG_CONF']
                    OCCURANCE = RESULT['OCCURANCE']
                    MESSAGE = f"BATCH ID: {BATCH_ID} HAD A RESULT OF: \n    {EMOTION} \n    {AVG_CONFIDENCE}% \nBASED ON A SAMPLE OF {FRAME_QNT} WITH AN OCCURANCE OF {OCCURANCE}\n---------------------------------------------\n"
                    write_to_file(MESSAGE)
                except multiprocessing.queues.Empty:
                    continue
            except queue.Empty:
                continue
    except KeyboardInterrupt:
        CPM_HALT.set()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()