# imports
from audio_module import audio_recorder
from cpm import scheduler
from debug import logger
from queue import Queue
import threading
import queue

# vars
RECORDING_ACTIVE = True
RECORDING_DURATION = 4.0
ANALYSIS_DURATION = 5.0
BUFFER = []
batch_id = 0
CONTROLLER_STOP = threading.Event()
CONTROLLER_THREAD = None

# queues
R2C = Queue(maxsize=1)

# helper functions
def initialize(AC2C, AI_READY):
    global CONTROLLER_THREAD
    logger.main('system', 'INITIALIZING AUDIO CONTROLLER')
    logger.main('audio_controller', 'INITIALIZING AUDIO CONTROLLER')
    CONTROLLER_THREAD = threading.Thread(target=main, args=(AC2C, AI_READY), daemon=False, name="ac_main")
    CONTROLLER_THREAD.start()

def clean_up():
    CONTROLLER_STOP.set()
    audio_recorder.clean_up()
    if CONTROLLER_THREAD is not None:
        CONTROLLER_THREAD.join(timeout=2.0)
    # print("SHUTTING DOWN AUDIO CONTROLLER")
    while not R2C.empty():
        try:
            _ = R2C.get_nowait()
        except queue.Empty:
            break
    # print("AUDIO CONTROLLER TERMINATED")

# main
def main(AC2C, AI_READY):
    global RECORDING_ACTIVE, batch_id
    audio_recorder.initialize(R2C, AI_READY)
    while not CONTROLLER_STOP.is_set():
        while not scheduler.signals.ac_start.wait(timeout=0.05):
            if CONTROLLER_STOP.is_set():
                return
        if CONTROLLER_STOP.is_set():
            break
        BUFFER.clear()
        RECORDING_ACTIVE = True
        while not scheduler.signals.audio_arrive.wait(timeout=0.05):
            if CONTROLLER_STOP.is_set():
                return
        if CONTROLLER_STOP.is_set():
            break
        while scheduler.signals.audio_arrive.is_set():
            if CONTROLLER_STOP.is_set():
                return
            try:
                recording = R2C.get(timeout=0.01)
            except queue.Empty:
                continue
            if RECORDING_ACTIVE:
                BUFFER.append(recording)
        try:
            batch_id += 1
            if len(BUFFER) == 0:
                AC2C.put({
                    "BUFFER": None,
                    "SOURCE": 2,
                    "BATCH": batch_id
                }, block=False)
                logger.main('audio_controller', f"SENDING BUFFER BATCH {batch_id} OF SIZE 0")
            else:
                AC2C.put({
                    "BUFFER": BUFFER.copy(),
                    "SOURCE": 2,
                    "BATCH": batch_id
                }, block=False)
                logger.main('audio_controller', f"SENDING BUFFER BATCH {batch_id} OF SIZE {len(BUFFER)}")
                logger.main('audio_controller', f"BUFFER BATCH {batch_id} CONSISTS OF ID(S) {', '.join(str(r['ID']) for r in BUFFER)}")
                logger.main('audio_controller', f"BUFFER BATCH {batch_id} CONSISTS OF FILE LENGTH(S) {', '.join(str(r['AUDIO'].shape[0]/16000) for r in BUFFER)}")
        except queue.Full:
            pass
        BUFFER.clear()
        RECORDING_ACTIVE = False