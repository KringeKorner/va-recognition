# imports
import sounddevice as sd
import threading
import time
import queue

# vars
DURATION=2
DEVICE=0 # Set this to whatever the device port is
fs=48000
ID=0
RECORDING_STOP=threading.Event()
RECORDER_THREAD=None

# helper functions
def initialize(R2C):
    global RECORDER_THREAD
    print("INITIALIZING AUDIO RECORDING")
    if DEVICE is not None:
        print("USING AUDIO DEVICE:",DEVICE)
    RECORDER_THREAD=threading.Thread(target=main,args=(R2C,),daemon=False)
    RECORDER_THREAD.start()

def clean_up():
    print("STOPPING AUDIO RECORDING")
    RECORDING_STOP.set()
    if RECORDER_THREAD is not None:
        print("STOPPING THREAD")
        RECORDER_THREAD.join(timeout=2.0)
        print("THREAD ALIVE:",RECORDER_THREAD.is_alive())
    print("AUDIO RECORDER TERMINATED")
    time.sleep(1.0)

# main
def main(R2C):
    global ID
    while True:
        if RECORDING_STOP.is_set():
            break
        try:
            recording=sd.rec(int(DURATION*fs),samplerate=fs,channels=1,dtype='float32',device=DEVICE)
            sd.wait()
        except Exception as e:
            print("AUDIO RECORD ERROR:",e)
            time.sleep(0.2)
            continue
        if recording is None:
            time.sleep(0.01)
            continue
        try:
            ID+=1
            AUDIO_SENT={"ID":ID,"AUDIO":recording}
            R2C.put(AUDIO_SENT,block=False)
        except queue.Full:
            time.sleep(0.05)
