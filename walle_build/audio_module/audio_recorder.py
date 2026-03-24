# imports
from debug import logger
import sounddevice as sd
import threading
import time
import queue

# vars
DURATION=2
DEVICE=None
fs=16000
ID=0
RECORDING_STOP=threading.Event()
RECORDER_THREAD=None

# helper functions
def initialize(R2C,AI_READY):
    global RECORDER_THREAD
    logger.main('system','INITIALIZING AUDIO RECORDING')
    logger.main('audio_recorder','INITIALIZING AUDIO RECORDING')
    RECORDER_THREAD=threading.Thread(target=main,args=(R2C,AI_READY),daemon=False,name="ar_main")
    RECORDER_THREAD.start()

def clean_up():
    logger.main('system','STOPPING AUDIO RECORDER')
    logger.main('audio_recorder','STOPPING AUDIO RECORDER')
    RECORDING_STOP.set()
    if RECORDER_THREAD is not None:
        RECORDER_THREAD.join(timeout=2.0)
    logger.main('system','AUDIO RECORDER TERMINATED')
    logger.main('audio_recorder','AUDIO RECORDER TERMINATED')
    time.sleep(1.0)

# main
def main(R2C,AI_READY):
    global ID
    AI_READY.wait()
    while True:
        if RECORDING_STOP.is_set():
            break
        try:
            recording=sd.rec(int(DURATION*fs),samplerate=fs,channels=1,dtype='float32',device=DEVICE)
            sd.wait()
        except Exception as e:
            logger.main('audio_recorder',f"AUDIO RECORDING ERROR: {e}")
            time.sleep(0.2)
            continue
        if recording is None:
            continue
        try:
            ID+=1
            AUDIO_SENT={"ID":ID,"AUDIO":recording}
            logger.main('audio_recorder',f"SENDING AUDIO FILE WITH ID {ID} OF SIZE {recording.shape[0]/fs:.3f}S")
            R2C.put(AUDIO_SENT,block=False)
        except queue.Full:
            time.sleep(0.05)