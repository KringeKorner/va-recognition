# imports
from audio_module import audio_recorder
from queue import Queue
import threading
import time
import queue

# vars
RECORDING_ACTIVE=True
RECORDING_DURATION=4.0
ANALYSIS_DURATION=5.0
BUFFER=[]
CONTROLLER_STOP=threading.Event()
CONTROLLER_THREAD=None

# queues
R2C=Queue(maxsize=1)

# helper functions
def initialize(AC2C):
    global CONTROLLER_THREAD
    print("INITIALIZING AUDIO CONTROLLER")
    CONTROLLER_THREAD=threading.Thread(target=main,args=(AC2C,),daemon=False)
    CONTROLLER_THREAD.start()

def clean_up():
    CONTROLLER_STOP.set()
    audio_recorder.clean_up()
    if CONTROLLER_THREAD is not None:
        print("STOPPING THREAD")
        CONTROLLER_THREAD.join(timeout=2.0)
        print("THREAD ALIVE:",CONTROLLER_THREAD.is_alive())
    print("SHUTTING DOWN AUDIO CONTROLLER")
    while not R2C.empty():
        try:
            _=R2C.get_nowait()
        except queue.Empty:
            break
    print("AUDIO CONTROLLER TERMINATED")

# main
def main(AC2C):
    global RECORDING_ACTIVE
    audio_recorder.initialize(R2C)
    CYCLE_START=time.monotonic()
    while True:
        if CONTROLLER_STOP.is_set():
            break
        ANALYSIS_START=time.monotonic()
        elapsed=ANALYSIS_START-CYCLE_START
        if elapsed>=ANALYSIS_DURATION:
            CYCLE_START=ANALYSIS_START
            BUFFER.clear()
            RECORDING_ACTIVE=True
        elif elapsed>=RECORDING_DURATION:
            RECORDING_ACTIVE=False
        if RECORDING_ACTIVE:
            try:
                recording=R2C.get(timeout=0.2)
                BUFFER.append(recording)
            except queue.Empty:
                time.sleep(0.01)
                continue
        else:
            try:
                if len(BUFFER)==0:
                    AC2C.put({"BUFFER":None,"SOURCE":2,"TIMESTAMP":CYCLE_START},block=False)
                else:
                    AC2C.put({"BUFFER":BUFFER.copy(),"SOURCE":2,"TIMESTAMP":CYCLE_START},block=False)
            except queue.Full:
                time.sleep(0.01)
                continue
            BUFFER.clear()