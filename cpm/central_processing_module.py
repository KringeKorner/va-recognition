# imports
from aai.CANDIDATE_1.FunASR import AAI
from audio_module import audio_controller
from enum import Enum
from pathlib import Path
from vai.CANDIDATE_1.Deepface import VAI
from video_module import video_controller
from queue import Queue
import cv2 as cv
import keyboard
import multiprocessing
from pathlib import Path
import threading
import queue

# vars
AAI_HALT = multiprocessing.Event()
AAI_READY = multiprocessing.Event()
AUDIOS = []
BATCH_ID = 0
CPM_HALT = threading.Event()
VC2C_MAX = 30
FRAMES = []
VAI_HALT = multiprocessing.Event()
VAI_READY = multiprocessing.Event()
ROOT_PATH = Path(__file__).resolve().parent
DEBUG_PATH = Path(ROOT_PATH).parent / 'video_module' / 'DEBUG'
CPM_LOGGER_PATH = Path(DEBUG_PATH) / 'CPM_LOGGER.txt'

# queues
VC2C = Queue(maxsize=1)
AC2C = Queue(maxsize=1)
C2V = multiprocessing.Queue(maxsize=1)
C2A = multiprocessing.Queue(maxsize=1)
V2C = multiprocessing.Queue(maxsize=1)
A2C = multiprocessing.Queue(maxsize=1)

# classes
class SOURCE(Enum):
    VIDEO = 1
    AUDIO = 2

# helper functions
def clean_up():
    print("SHUTTING DOWN CPM")
    VAI.clean_up(C2V, VAI_HALT)
    AAI.clean_up(C2A, AAI_HALT)
    video_controller.clean_up()
    audio_controller.clean_up()
    
    while not VC2C.empty():
        try:
            _ = VC2C.get_nowait()
        except queue.Empty:
            break
    while not V2C.empty():
        try:
            _ = V2C.get_nowait()
        except queue.Empty:
            break
    while not AC2C.empty():
        try:
            _ = AC2C.get_nowait()
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
    AAI.initialize(C2A, A2C, AAI_HALT, AAI_READY)
    VAI_READY.wait()
    AAI_READY.wait()
    video_controller.initialize(VC2C)
    audio_controller.initialize(AC2C)
    try:
        while not CPM_HALT.is_set():
            if keyboard.is_pressed('q'):
                CPM_HALT.set()
                clean_up()
                break
            try:
                BATCH_ID += 1
                VIDEO_PACKET = VC2C.get(timeout=1/VC2C_MAX)
                AUDIO_PACKET = AC2C.get(timeout=0.2)
                VIDEO_BUFFER_SOURCE = SOURCE(VIDEO_PACKET['SOURCE'])
                AUDIO_BUFFER_SOURCE = SOURCE(AUDIO_PACKET['SOURCE'])
                FRAME_QNT = len(VIDEO_PACKET['BUFFER'])
                AUDIO_QNT = len(AUDIO_PACKET['BUFFER'])
                for RESPONSE in VIDEO_PACKET['BUFFER']:
                    FRAMES.append(RESPONSE['FRAME']['FRAME'])
                for AUDIO in AUDIO_PACKET['BUFFER']:
                    AUDIOS.append(AUDIO['AUDIO'])
                print(f"Received VIDEO_PACKET from: {VIDEO_BUFFER_SOURCE} of size {FRAME_QNT}")
                print(f"Received AUDIO_PACKET from: {AUDIO_BUFFER_SOURCE} of size {AUDIO_QNT}")
                try:
                    print(f"Sending {len(FRAMES)} to VAI")
                    C2V.put(FRAMES.copy(), block=False)
                    print(f"Sending {len(AUDIOS)} to AAI")
                    C2A.put(AUDIOS.copy(), block=False)
                except multiprocessing.queues.Full:
                    FRAMES.clear()
                    AUDIOS.clear()
                    continue
                FRAMES.clear()
                AUDIOS.clear()
                try:
                    V_RESULT = V2C.get(timeout=1/FRAME_QNT)
                    V_EMOTION = V_RESULT['EMOTION']
                    V_AVG_CONFIDENCE = V_RESULT['AVG_CONF']
                    V_OCCURANCE = V_RESULT['OCCURANCE']
                    V_MESSAGE = f"BATCH ID: {BATCH_ID} HAD A RESULT OF: \n    {V_EMOTION} \n    {V_AVG_CONFIDENCE}% \nBASED ON A SAMPLE OF {FRAME_QNT} WITH AN OCCURANCE OF {V_OCCURANCE}\n---------------------------------------------\n"
                    write_to_file(V_MESSAGE)
                except multiprocessing.queues.Empty:
                    continue
                try:
                    A_RESULT = A2C.get(timeout=0.2)
                    A_EMOTION = A_RESULT['EMOTION']
                    A_AVG_CONFIDENCE = A_RESULT['AVG_CONF']
                    A_LABELS = A_RESULT['LABELS']
                    A_MESSAGE = f"BATCH ID: {BATCH_ID} HAD A RESULT OF: \n    {A_EMOTION} \n    {A_AVG_CONFIDENCE}% \nFROM A SAMPLE RANGE OF:\n{A_LABELS}\n---------------------------------------------\n"
                    write_to_file(A_MESSAGE)
                except multiprocessing.queues.Empty:
                    continue
            except queue.Empty:
                continue
    except KeyboardInterrupt:
        CPM_HALT.set()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()