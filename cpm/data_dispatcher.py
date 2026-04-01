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
# PORT = "COM4"
PORT = "COM11"
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

class LANDMARK(Enum):
    NO_LANDMARK = 0
    GENERAL_LANDMARK = 1
    KEY_LANDMARK = 2

# helper functions
def initialize(C2D, AI_READY, BYPASS = False):
    global DISPATCHER_THREAD
    logger.main('system', 'INITIALIZING DATA DISPATCHER')
    logger.main('dispatcher', 'INITIALIZING DATA DISPATCHER')
    DISPATCHER_THREAD = threading.Thread(target=main, args=(C2D, AI_READY, BYPASS), daemon=False,name="dispatcher")
    DISPATCHER_THREAD.start()

def bundle_packet(asource, vsource, mood, confidence, landmark):
    mood = mood.upper()
    vsource = vsource.upper()
    asource = asource.upper()
    packet = []
    if (asource == "NONE" and vsource == "NONE"):
        source = "NONE"
        landmark = LANDMARK(0).value
    elif (asource != "NONE" and vsource == "NONE"):
        source = "AUDIO"
        landmark = LANDMARK(0).value
    elif (asource == "NONE" and vsource != "NONE"):
        source = "VIDEO"
        landmark = LANDMARK[landmark].value
    elif (asource != "NONE" and vsource != "NONE"):
        source = "BOTH"
        landmark = LANDMARK[landmark].value
    source_bit = SOURCE[source].value
    mood_bit = MOOD[mood].value
    confidence = int(round(confidence))
    packet = ['m', mood_bit, 's', source_bit, 'c', confidence, 'l', landmark]
    return packet

def clean_up(C2D, BYPASS):
    DISPATCHER_STOP.set()
    if BYPASS == False:
        ser.close()
        logger.main('system', 'CLOSING SERIAL CHANNEL')
        logger.main('dispatcher', 'CLOSING SERIAL CHANNEL')
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
def main(C2D, AI_READY, BYPASS):
    if BYPASS:
        logger.main('system', "BYPASS SELECTED, NO SERIAL CONNECTION NEEDED")
        logger.main('dispatcher', "BYPASS SELECTED, NO SERIAL CONNECTION NEEDED")
        AI_READY.wait()
        while not DISPATCHER_STOP.is_set():
            try:
                results = C2D.get_nowait()
                asource = results['ASOURCE']
                vsource = results['VSOURCE']
                mood = results['MOOD']
                confidence = results['CONFIDENCE']
                landmark = results['LANDMARK']
                message = f"RECEIVED {mood} WITH {confidence}% CONFIDENCE WITH SOURCE(S) {asource}(A) AND {vsource}(V) WITH COMMON LANDMARK {landmark} "
                logger.main('dispatcher', message)
                packet = bundle_packet(asource, vsource, mood, confidence, landmark)
                if not DISPATCHER_STOP.is_set():
                    message = f"BUNDLED PACKET {packet}"
                    logger.main('dispatcher', message)
            except queue.Empty:
                continue
    else:
        global ser
        ser = serial.Serial(PORT, BAUD, timeout=1)
        message = f"OPENING SERIAL COMMUNICATION OVER {PORT} WITH BAUD RATE {BAUD}"
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
                    asource = results['ASOURCE']
                    vsource = results['VSOURCE']
                    mood = results['MOOD']
                    confidence = results['CONFIDENCE']
                    landmark = results['LANDMARK']
                    message = f"RECEIVED {mood} WITH {confidence}% CONFIDENCE WITH SOURCE(S) {asource}(A) AND {vsource}(V) WITH COMMON LANDMARK {landmark} "
                    logger.main('dispatcher', message)
                    packet = bundle_packet(asource, vsource, mood, confidence, landmark)
                    if not DISPATCHER_STOP.is_set():
                        message = f"SENDING PACKET {packet} OVER SERIAL"
                        logger.main('dispatcher', message)
                        ser.write(bytes(packet))
                except queue.Empty:
                    continue
            elif line: 
                message = f"RECEIVED {line} FROM ARDUINO OVER SERIAL"
                logger.main('dispatcher', message)