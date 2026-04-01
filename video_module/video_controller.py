# imports
from cpm import scheduler
from debug import logger
from pathlib import Path
from queue import Queue
from video_module import analyzer
from video_module import video_recorder
from video_module import minerva
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
R2C = Queue(maxsize=10)
C2A = Queue(maxsize=5)
A2C = Queue(maxsize=5)

# helper functions
def initialize(VC2C, AI_READY, DEBUG_MODE, MINERVA_CAPTURE):
    global CONTROLLER_THREAD
    logger.main('system', 'INITIALIZING VIDEO CONTROLLER')
    logger.main('video_controller', 'INITIALIZING VIDEO CONTROLLER')
    CONTROLLER_THREAD = threading.Thread(
        target=main,
        args=(VC2C, AI_READY, DEBUG_MODE, MINERVA_CAPTURE),
        daemon=False,
        name="vc_thread"
    )
    CONTROLLER_THREAD.start()

def clean_up():
    CONTROLLER_STOP.set()
    video_recorder.clean_up()
    analyzer.clean_up(C2A)
    # minerva cleanup
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

def drain_analyzer_results():
    appended = 0
    while True:
        try:
            response = A2C.get_nowait()
        except queue.Empty:
            break
        if response is None:
            continue
        if response['LANDMARK'] != 'NO_LANDMARK':
            BUFFER.append(response)
            appended += 1
    return appended

# main
def main(VC2C, AI_READY, DEBUG_MODE, MINERVA_CAPTURE):
    global ACTIVE, batch_id
    video_recorder.initialize(R2C, AI_READY, MINERVA_CAPTURE)
    analyzer.initialize(C2A, A2C, DEBUG_MODE, AI_READY)
    minerva.initialize(DEBUG_MODE)
    while not CONTROLLER_STOP.is_set():
        while not scheduler.signals.vc_start.wait(timeout=0.05):
            if CONTROLLER_STOP.is_set():
                return
        if CONTROLLER_STOP.is_set():
            return
        BUFFER.clear()
        ACTIVE = True
        while not scheduler.signals.frames_arrive.is_set():
            if CONTROLLER_STOP.is_set():
                return
            pushed = 0
            while True:
                try:
                    frame = R2C.get_nowait()
                except queue.Empty:
                    break
                try:
                    C2A.put_nowait(frame)
                    pushed += 1
                except queue.Full:
                    break
            drain_analyzer_results()
            if pushed == 0:
                threading.Event().wait(0.002)
        final_deadline = threading.Event()
        end_time = 0.03
        import time
        start = time.perf_counter()
        while time.perf_counter() - start < end_time:
            if CONTROLLER_STOP.is_set():
                return
            drain_analyzer_results()
            threading.Event().wait(0.002)
        try:
            batch_id += 1
            if len(BUFFER) == 0:
                VC2C.put({
                    "BUFFER": None,
                    "SOURCE": 1,
                    "BATCH": batch_id
                }, block=False)
                minerva.drop_batch("VIDEO CONTROLLER", "EMPTY BUFFER, NO VALID FRAMES FOR EMOTIONAL ANALYSIS")
                logger.main('video_controller', f"SENDING BUFFER BATCH {batch_id} OF SIZE 0")
            else:
                VC2C.put({
                    "BUFFER": BUFFER.copy(),
                    "SOURCE": 1,
                    "BATCH": batch_id
                }, block=False)
                logger.main('video_controller', f"SENDING BUFFER BATCH {batch_id} OF SIZE {len(BUFFER)}")
                logger.main(
                    'video_controller',
                    f"BUFFER BATCH {batch_id} CONSISTS OF ID(S) {', '.join(str(r['FRAME']['ID']) for r in BUFFER)}"
                )
                logger.main(
                    'video_controller',
                    f"BUFFER BATCH {batch_id} CONSISTS OF LANDMARK(S) {', '.join(str(r['LANDMARK']) for r in BUFFER)}"
                )
        except queue.Full:
            pass
        BUFFER.clear()
        ACTIVE = False
        while scheduler.signals.frames_arrive.is_set():
            if CONTROLLER_STOP.is_set():
                return
            threading.Event().wait(0.005)