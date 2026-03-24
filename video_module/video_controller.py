# imports
from cpm import scheduler
from debug import logger
from pathlib import Path
from queue import Queue
from video_module import analyzer
from video_module import video_recorder
import threading
import queue

# vars
ACTIVE = True
BUFFER = []
batch_id = 0
CONTROLLER_STOP = threading.Event()
CONTROLLER_THREAD = None
ROOT_PATH = Path(__file__).resolve().parent
FRAMES = []

# queues
R2C = Queue(maxsize=1)
C2A = Queue(maxsize=1)
A2C = Queue(maxsize=1)

# helper functions
def initialize(VC2C, AI_READY):
    global CONTROLLER_THREAD
    logger.main('system', 'INITIALIZING VIDEO CONTROLLER')
    logger.main('video_controller', 'INITIALIZING VIDEO CONTROLLER')
    CONTROLLER_THREAD = threading.Thread(target=main, args=(VC2C, AI_READY), daemon=False, name="vc_thread")
    CONTROLLER_THREAD.start()

def clean_up():
    CONTROLLER_STOP.set()
    video_recorder.clean_up()
    analyzer.clean_up(C2A)
    if CONTROLLER_THREAD is not None:
        CONTROLLER_THREAD.join(timeout=2.0)
    logger.main('system', 'SHUTTING DOWN VIDEO CONTROLLER')
    logger.main('video_controller', 'SHUTTING DOWN VIDEO CONTROLLER')
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
    logger.main('system', 'VIDEO CONTROLLER TERMINATED')
    logger.main('video_controller', 'VIDEO CONTROLLER TERMINATED')

# main
def main(VC2C, AI_READY):
    global ACTIVE, batch_id
    video_recorder.initialize(R2C, AI_READY)
    analyzer.initialize(C2A, A2C, False, AI_READY)
    while not CONTROLLER_STOP.is_set():
        while not scheduler.signals.vc_start.wait(timeout=0.05):
            if CONTROLLER_STOP.is_set():
                return
        if CONTROLLER_STOP.is_set():
            break
        BUFFER.clear()
        ACTIVE = True
        while not scheduler.signals.frames_arrive.wait(timeout=0.05):
            if CONTROLLER_STOP.is_set():
                return
        if CONTROLLER_STOP.is_set():
            break
        while scheduler.signals.frames_arrive.is_set():
            if CONTROLLER_STOP.is_set():
                return
            try:
                FRAME = R2C.get(timeout=0.01)
            except queue.Empty:
                continue
            try:
                C2A.put(FRAME, timeout=0.01)
            except queue.Full:
                continue
            if ACTIVE:
                try:
                    RESPONSE = A2C.get(timeout=0.01)
                    if RESPONSE['LANDMARK'] != 'NO_LANDMARK':
                        BUFFER.append(RESPONSE)
                except queue.Empty:
                    continue
        try:
            batch_id += 1
            if len(BUFFER) == 0:
                VC2C.put({
                    "BUFFER": None,
                    "SOURCE": 1,
                    "BATCH": batch_id
                }, block=False)
                logger.main('video_controller', f"SENDING BUFFER BATCH {batch_id} OF SIZE 0")
            else:
                VC2C.put({
                    "BUFFER": BUFFER,
                    "SOURCE": 1,
                    "BATCH": batch_id
                }, block=False)
                logger.main('video_controller', f"SENDING BUFFER BATCH {batch_id} OF SIZE {len(BUFFER)}")
                logger.main('video_controller', f"BUFFER BATCH {batch_id} CONSISTS OF ID(S) {', '.join(str(r['FRAME']['ID']) for r in BUFFER)}")
                logger.main('video_controller', f"BUFFER BATCH {batch_id} CONSISTS OF LANDMARK(S) {', '.join(str(r['LANDMARK']) for r in BUFFER)}")
        except queue.Full:
            pass
        BUFFER.clear()
        ACTIVE = False