# imports
from enum import Enum
from pathlib import Path
from queue import Queue
import os
import serial
import threading
import time
import queue

# vars
DISPATCHER_THREAD=None
DISPATCHER_STOP=threading.Event()
PORT="/dev/ttyACM0"  # Pi serial port
BAUD=115200

# classes
class SOURCE(Enum):
    NONE=0
    AUDIO=1
    VIDEO=2
    BOTH=3

class MOOD(Enum):
    NONE=0
    ANGRY=1
    DISGUST=2
    FEAR=3
    HAPPY=4
    SAD=5
    SURPRISE=6
    NEUTRAL=7

# helper functions
def initialize(C2D):
    global DISPATCHER_THREAD
    print("INITIALIZING DATA DISPATCHER")
    DISPATCHER_THREAD=threading.Thread(target=main,args=(C2D,),daemon=False)
    DISPATCHER_THREAD.start()

def bundle_packet(mood,vsource,asource):
    global ser
    mood=mood.upper()
    vsource=vsource.upper()
    asource=asource.upper()
    line=ser.readline().decode().strip()
    if asource=="NONE" and vsource=="NONE":source="NONE"
    elif asource!="NONE" and vsource=="NONE":source="AUDIO"
    elif asource=="NONE" and vsource!="NONE":source="VIDEO"
    elif asource!="NONE" and vsource!="NONE":source="BOTH"
    source_bit=SOURCE[source].value
    mood_bit=MOOD[mood].value
    if line=="READY":
        print("Sending:",source_bit,mood_bit)
        ser.write(bytes([source_bit,mood_bit]))

def clean_up(C2D):
    DISPATCHER_STOP.set()
    print("CLOSING SERIAL CHANNEL")
    ser.close()
    if DISPATCHER_THREAD is not None:
        print("SHUTTING DOWN DATA DISPATCHER")
        DISPATCHER_THREAD.join(timeout=2.0)
        print("THREAD ALIVE:",DISPATCHER_THREAD.is_alive())
    while not C2D.empty():
        try:_=C2D.get_nowait()
        except queue.Empty:break
    print("DATA DISPATCHER TERMINATED")

# main
def main(C2D):
    global ser
    ser=serial.Serial(PORT,BAUD,timeout=1)
    ser.setDTR(False)
    time.sleep(1)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    ser.setDTR(True)
    print("SERIAL CHANNEL IS ONLINE")
    while not DISPATCHER_STOP.is_set():
        try:
            results=C2D.get(timeout=0.2)
            vsource=results['VSOURCE']
            asource=results['ASOURCE']
            mood=results['MOOD']
            confidence=results['CONFIDENCE']
            print(f"Received {mood} with {confidence}% confidence with source(s) {vsource} and {asource}")
            bundle_packet(mood,asource,vsource)
        except queue.Empty:
            continue