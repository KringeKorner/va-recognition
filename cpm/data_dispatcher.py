# imports
from enum import Enum
from debug import logger
from pathlib import Path
from queue import Queue
import numpy as np
import os
import serial
import serial.tools.list_ports
import threading
import time
import queue

# vars
DISPATCHER_THREAD = None
DISPATCHER_STOP = threading.Event()
PORT = "COM4"
# PORT = "COM11"
# PORT = "/dev/ttyACM0"
BAUD = 115200

# classes
class SOURCE(Enum):
    NONE = 0
    AUDIO = 1
    VIDEO = 2
    BOTH = 3

class MOOD(Enum):
    NONE = 0
    ANGRY = 1
    DISGUST = 2
    FEAR = 3
    HAPPY = 4
    SAD = 5
    SURPRISE = 6
    NEUTRAL = 7

# helper functions
def initialize(C2D, AI_READY):
    global DISPATCHER_THREAD
    logger.main('system', 'INITIALIZING DATA DISPATCHER')
    logger.main('dispatcher', 'INITIALIZING DATA DISPATCHER')
    DISPATCHER_THREAD = threading.Thread(target=main, args=(C2D, AI_READY), daemon=False,name="dispatcher")
    DISPATCHER_THREAD.start()

def bundle_packet(mood, asource, vsource):
    mood = mood.upper()
    vsource = vsource.upper()
    asource = asource.upper()
    packet = []
    if (asource == "NONE" and vsource == "NONE"):
        source = "NONE"
    elif (asource != "NONE" and vsource == "NONE"):
        source = "AUDIO"
    elif (asource == "NONE" and vsource != "NONE"):
        source = "VIDEO"
    elif (asource != "NONE" and vsource != "NONE"):
        source = "BOTH"
    source_bit = SOURCE[source].value
    mood_bit = MOOD[mood].value
    packet = [source_bit, mood_bit]
    return packet

def clean_up(C2D):
    DISPATCHER_STOP.set()
    logger.main('system', 'CLOSING SERIAL CHANNEL')
    logger.main('dispatcher', 'CLOSING SERIAL CHANNEL')
    ser.close()
    if DISPATCHER_THREAD is not None:
        logger.main('system', 'SHUTTING DOWN DATA DISPATCHER')
        logger.main('dispatcher', 'SHUTTING DOWN DATA DISPATCHER')
        DISPATCHER_THREAD.join(timeout=2.0)
    while not C2D.empty():
        try:
            _ = C2D.get_nowait()
        except queue.Empty:
            break
    logger.main('system', 'DATA DISPATCHER TERMINATED')
    logger.main('dispatcher', 'DATA DISPATCHER TERMINATED')

# main
def main(C2D, AI_READY):
    global ser
    ser = serial.Serial(PORT, BAUD, timeout=1)
    message = f"OPEN SERIAL COMMUNICATION OVER {PORT} WITH BAUD RATE {BAUD}"
    logger.main('dispatcher', message)
    time.sleep(2)
    ser.setDTR(False)
    time.sleep(1)
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    ser.setDTR(True)
    logger.main('system', 'SERIAL CHANNEL IS ONLINE')
    logger.main('dispatcher', 'SERIAL CHANNEL IS ONLINE')
    AI_READY.wait()
    while not DISPATCHER_STOP.is_set():
        line = ser.readline().decode('ascii', errors='ignore').strip()
        if line == "READY":
            try:
                results = C2D.get_nowait()
                vsource = results['VSOURCE']
                asource = results['ASOURCE']
                mood = results['MOOD']
                confidence = results['CONFIDENCE']
                message = f"RECEIVED {mood} WITH {confidence}% CONFIDENCE WITH SOURCE(S) {asource}(A) AND {vsource}(V)"
                logger.main('dispatcher', message)
                packet = bundle_packet(mood, asource, vsource)
                if not DISPATCHER_STOP.is_set():
                    message = f"SENDING PACKET {packet} OVER SERIAL"
                    logger.main('dispatcher', message)
                    ser.write(bytes(packet))
            except queue.Empty:
                continue
        elif line: 
            message = f"RECEIVED {line} FROM ARDUINO OVER SERIAL"
            logger.main('dispatcher', message)