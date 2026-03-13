# imports
from aai.CANDIDATE_1.FunASR import AAI
from audio_module import audio_controller
from cpm import data_dispatcher
from enum import Enum
from pathlib import Path
from vai.CANDIDATE_1.Deepface import VAI
from video_module import video_controller
from queue import Queue
import cv2 as cv
import keyboard
import multiprocessing
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
C2D = Queue(maxsize=1)
C2V = multiprocessing.Queue(maxsize=1)
C2A = multiprocessing.Queue(maxsize=1)
V2C = multiprocessing.Queue(maxsize=1)
A2C = multiprocessing.Queue(maxsize=1)

# classes
class SOURCE(Enum):
    NONE = 0
    VIDEO = 1
    AUDIO = 2

# helper functions
def clean_up():
    print("SHUTTING DOWN CPM")
    data_dispatcher.clean_up(C2D)
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

def fusion(vlabels, alabels, vai_results, aai_results):
    a_weight = 0.538
    v_weight = 0.462
    if vai_results == 0 and aai_results == 0:
        final_conf = 0
        final_mood = "NONE"
    elif vai_results == 0 and aai_results != 0:
        final_conf = max(aai_results)
        final_mood = alabels[aai_results.index(final_conf)]
    elif vai_results != 0 and aai_results == 0:
        final_conf = max(vai_results)
        final_mood = vlabels[vai_results.index(final_conf)]
    else:
        weighted_AAI = [a * a_weight for a in aai_results]
        weighted_VAI = [v * v_weight for v in vai_results]
        fused_conf = [round((v + a), 3) for v, a in zip(weighted_VAI, weighted_AAI)]
        final_conf = max(fused_conf)
        final_mood = vlabels[fused_conf.index(final_conf)]
    return(final_mood, final_conf)

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
    data_dispatcher.initialize(C2D)
    try:
        while not CPM_HALT.is_set():
            if keyboard.is_pressed('q'):
                CPM_HALT.set()
                clean_up()
                break
            try:
                VIDEO_PACKET = VC2C.get(timeout=0.2)
                VIDEO_BUFFER_SOURCE = SOURCE(VIDEO_PACKET['SOURCE']).name
                if VIDEO_PACKET['BUFFER'] is None:
                    vlabels = None
                    vac = 0
                    VIDEO_BUFFER_SOURCE = "NONE"
                else:
                    for RESPONSE in VIDEO_PACKET['BUFFER']:
                        FRAMES.append(RESPONSE['FRAME']['FRAME'])
                    try:
                        C2V.put(FRAMES.copy(), block=False)
                    except multiprocessing.queues.Full:
                        FRAMES.clear()
                    try:
                        V_RESULT = V2C.get(timeout=0.2)
                        vlabels = V_RESULT['LABELS']
                        vac = V_RESULT['AVG_CONF']
                    except multiprocessing.queues.Empty:
                        continue
            except queue.Empty:
                continue
            try:
                AUDIO_PACKET = AC2C.get(timeout=0.2)
                AUDIO_BUFFER_SOURCE = SOURCE(AUDIO_PACKET['SOURCE']).name
                if AUDIO_PACKET['BUFFER'] is None:
                    alabels = None
                    aac = 0
                    AUDIO_BUFFER_SOURCE = "NONE"
                else:
                    for AUDIO in AUDIO_PACKET['BUFFER']:
                        AUDIOS.append(AUDIO['AUDIO'])
                    try:
                        C2A.put(AUDIOS.copy(), block=False)
                    except multiprocessing.queues.Full:
                        AUDIOS.clear()
                        continue
                    AUDIOS.clear()
                    try:
                        A_RESULT = A2C.get(timeout=0.2)
                        alabels = A_RESULT['LABELS']
                        aac = A_RESULT['AVG_CONF']
                    except multiprocessing.queues.Empty:
                        continue
            except queue.Empty:
                continue
            mood, confidence = fusion(vlabels, alabels, vac, aac)
            packet = {
                'VSOURCE' : VIDEO_BUFFER_SOURCE,
                'ASOURCE' : AUDIO_BUFFER_SOURCE,
                'MOOD' : mood,
                'CONFIDENCE' : confidence,
            }
            try:
                C2D.put(packet, block=False)
            except queue.Full:
                continue
    except KeyboardInterrupt:
        CPM_HALT.set()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()