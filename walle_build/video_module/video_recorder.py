# imports
from imutils.video import VideoStream as vs
from debug import logger
import threading
import time
import queue

# vars
CAM_SRC=0
CAM_RES=(1280,720)
FRAME_RATE=30
ID=0
RECORDING_STOP=threading.Event()
RECORDER_THREAD=None
STREAM=None

# helper functions
def initialize(QUEUE,AI_READY):
    global STREAM,RECORDER_THREAD,ID
    logger.main('system','INITIALIZING VIDEO RECORDER')
    logger.main('video_recorder','INITIALIZING VIDEO RECORDER')
    RECORDING_STOP.clear()
    ID=0
    STREAM=vs(src=CAM_SRC,resolution=CAM_RES,framerate=FRAME_RATE).start()
    time.sleep(0.5)
    RECORDER_THREAD=threading.Thread(target=main,args=(STREAM,QUEUE,AI_READY),daemon=False,name="video_recorder_main")
    RECORDER_THREAD.start()

def clean_up():
    global STREAM,RECORDER_THREAD
    logger.main('system','STOPPING VIDEO RECORDER')
    logger.main('video_recorder','STOPPING VIDEO RECORDER')
    RECORDING_STOP.set()
    if STREAM is not None:
        logger.main('video_recorder','STOPPING VIDEO STREAM')
        STREAM.stop()
        if hasattr(STREAM,"stream") and hasattr(STREAM.stream,"isOpened"):
            if STREAM.stream.isOpened():
                logger.main('video_recorder','FORCE RELEASING VIDEO CAPTURE')
                STREAM.stream.release()
    if RECORDER_THREAD is not None:
        RECORDER_THREAD.join(timeout=2.0)
        logger.main('video_recorder',f'RECORDER THREAD ALIVE: {RECORDER_THREAD.is_alive()}')
    logger.main('system','VIDEO RECORDER TERMINATED')
    logger.main('video_recorder','VIDEO RECORDER TERMINATED')
    time.sleep(0.5)

# main
def main(STREAM,QUEUE,AI_READY):
    global ID
    if STREAM is None:
        logger.main('system','VIDEO RECORDER FAILURE')
        return
    while not AI_READY.is_set():
        if RECORDING_STOP.is_set():
            return
        time.sleep(0.05)
    logger.main('video_recorder','READY RECEIVED')
    while True:
        if RECORDING_STOP.is_set():
            logger.main('video_recorder','STOP DETECTED, EXITING LOOP')
            break
        try:
            FRAME=STREAM.read()
        except Exception as e:
            logger.main('video_recorder',f'VIDEO READ ERROR: {e}')
            time.sleep(0.05)
            continue
        if FRAME is None:
            time.sleep(0.01)
            continue
        try:
            ID+=1
            FRAME_SENT={"ID":ID,"FRAME":FRAME}
            logger.main('video_recorder',f'CAPTURED FRAME WITH ID {ID}')
            QUEUE.put(FRAME_SENT,block=False)
        except queue.Full:
            time.sleep(0.01)