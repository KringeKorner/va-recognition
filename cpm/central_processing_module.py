# imports
from aai.CANDIDATE_1.FunASR import AAI
from audio_module import audio_controller
from collections import Counter
from cpm import data_dispatcher
from cpm import scheduler
from debug import logger
from enum import Enum
from pathlib import Path
from vai.CANDIDATE_1.Deepface import VAI
from video_module import minerva
from video_module import video_controller
from queue import Queue
import keyboard
import multiprocessing
import numpy as np
import threading
import queue
import time

# vars
AAI_HALT = multiprocessing.Event()
AAI_READY = multiprocessing.Event()
AI_READY = threading.Event()
analysis_cycle = 0
AUDIOS = []
CPM_HALT = threading.Event()
DEBUG_MODE = True # REMEMBER TO SET THIS ACCORDINGLY
VC2C_MAX = 30
FRAMES = []
VAI_HALT = multiprocessing.Event()
VAI_READY = multiprocessing.Event()
ROOT_PATH = Path(__file__).resolve().parent
MINERVA_CAPTURE = threading.Event()

# queues
VC2C = Queue(maxsize=1)
AC2C = Queue(maxsize=1)
C2D = Queue(maxsize=1)
C2V = multiprocessing.Queue(maxsize=1)
C2A = multiprocessing.Queue(maxsize=1)
V2C = multiprocessing.Queue(maxsize=1)
A2C = multiprocessing.Queue(maxsize=1)

# classes
class SOURCE(Enum):
    NONE = 0
    VIDEO = 1
    AUDIO = 2

class Flags:
    frames_arrived = False
    VAI_arrived = False
    audio_arrived = False
    AAI_arrived = False
flags = Flags()

# helper
def clean_up():
    logger.main('system', 'SHUTTING DOWN CPM')
    logger.main('cpm', 'SHUTTING DOWN CPM')
    scheduler.clean_up()
    video_controller.clean_up()
    audio_controller.clean_up()
    VAI.clean_up(C2V, VAI_HALT)
    AAI.clean_up(C2A, AAI_HALT)
    data_dispatcher.clean_up(C2D, True)
    while not VC2C.empty():
        try: VC2C.get_nowait()
        except queue.Empty: break
    while not V2C.empty():
        try: V2C.get_nowait()
        except queue.Empty: break
    while not AC2C.empty():
        try: AC2C.get_nowait()
        except queue.Empty: break
    logger.main('system', 'ACTIVATING MINERVA')
    minerva.activate()
    logger.main('system', 'CPM TERMINATED')
    logger.main('cpm', 'CPM TERMINATED')

def fusion(vlabels,alabels,vai_results,aai_results):
    a_weight=0.538
    v_weight=0.462
    if vai_results==0 and aai_results==0:
        message = f"NONE CASE RECEIVED FOR FUSION, RETURNING NONE CASE"
        logger.main('cpm', message)
        return "NONE",0,"NONE"
    if vai_results==0:
        m=max(aai_results)
        message = f"AUDIO ONLY RECEIVED, GRANTING FULL WEIGHTING TO AUDIO"
        logger.main('cpm', message)
        message = f"PRODUCED FINAL RESULT {alabels[aai_results.index(m)]} WITH CONFIDENCE {m}%"
        logger.main('cpm', message)
        return alabels[aai_results.index(m)],m, "AAI ONLY"
    if aai_results==0:
        m=max(vai_results)
        message = f"VIDEO ONLY RECEIVED, GRANTING FULL WEIGHTING TO VIDEO"
        logger.main('cpm', message)
        message = f"PRODUCED FINAL RESULT {vlabels[vai_results.index(m)]} WITH CONFIDENCE {m}%"
        logger.main('cpm', message)
        return vlabels[vai_results.index(m)],m, "VAI ONLY"
    wa=[a*a_weight for a in aai_results]
    wv=[v*v_weight for v in vai_results]
    fused=[round(v+a,3) for v,a in zip(wv,wa)]
    m=max(fused)
    message = f"AUDIO AND VIDEO SOURCES RECEIVED, FUSING WITH {a_weight}/{v_weight} WEIGHTING SPLIT"
    logger.main('cpm', message)
    message = f"PRODUCED FINAL RESULT {vlabels[fused.index(m)]} WITH CONFIDENCE {m}%"
    logger.main('cpm', message)
    return vlabels[fused.index(m)],m, "VAI, AAI"

def keyboard_listener():
    while not CPM_HALT.is_set():
        if keyboard.is_pressed('q'):
            CPM_HALT.set()
            break
        time.sleep(0.05)
# main
def main():
    global analysis_cycle
    threading.Thread(target=keyboard_listener,daemon=True,name="keyboard_thread").start()
    logger.initialize()
    logger.main('system', 'INITIALIZING CPM')
    logger.main('cpm', 'INITIALIZING CPM')
    logger.main('system', 'INITIATING BOOT SEQUENCES')
    logger.main('cpm', 'INITIATING BOOT SEQUENCES')
    VAI.initialize(C2V,V2C,VAI_HALT,VAI_READY)
    AAI.initialize(C2A,A2C,AAI_HALT,AAI_READY)
    VAI_READY.wait()
    AAI_READY.wait()
    logger.main('system', 'AI MODELS READY')
    logger.main('cpm', 'AI MODELS READY')
    AI_READY.set()
    video_controller.initialize(VC2C, AI_READY, DEBUG_MODE, MINERVA_CAPTURE)
    audio_controller.initialize(AC2C, AI_READY)
    data_dispatcher.initialize(C2D, AI_READY, True)
    scheduler.initialize()
    while not CPM_HALT.is_set():
        vlabels,vac=None,0
        alabels,aac=None,0
        most_common_landmark = 'NO_LANDMARK'
        VIDEO_BUFFER_SOURCE,AUDIO_BUFFER_SOURCE="NONE","NONE"
        FRAMES.clear()
        AUDIOS.clear()
        analysis_cycle += 1
        if minerva.should_sample(analysis_cycle):
            minerva.begin_batch(analysis_cycle)
            MINERVA_CAPTURE.set()
        else:
            MINERVA_CAPTURE.clear()
        message = f"INITIATING ANALYSIS CYCLE {analysis_cycle}"
        logger.main('cpm', message)
        scheduler.signals.frames_arrive.wait()
        flags.frames_arrived=False
        latest_video_pkt=None
        while scheduler.signals.frames_arrive.is_set():
            try:
                latest_video_pkt=VC2C.get(timeout=0.01)
            except queue.Empty:
                continue
        MINERVA_CAPTURE.clear()
        if latest_video_pkt is not None and latest_video_pkt['BUFFER'] is not None:
            VIDEO_BUFFER_SOURCE=SOURCE(latest_video_pkt['SOURCE']).name
            for f in latest_video_pkt['BUFFER']:
                FRAMES.append(f['FRAME']['FRAME'])
            flags.frames_arrived=True
            message = f"RECEIVED BUFFER FROM SOURCE {VIDEO_BUFFER_SOURCE} OF SIZE {len(latest_video_pkt['BUFFER'])}"
            logger.main('cpm', message)
            message = f"BUFFER HAS ID {latest_video_pkt['BATCH']} CONTAINING FRAME ID(S) {', '.join(str(p['FRAME']['ID']) for p in latest_video_pkt['BUFFER'])}"
            logger.main('cpm', message)
            landmarks = [frame['LANDMARK'] for frame in latest_video_pkt['BUFFER']]
            if landmarks:
                most_common_landmark = Counter(landmarks).most_common(1)[0][0]
            else:
                most_common_landmark = 'NO_LANDMARK'
        else:
            VIDEO_BUFFER_SOURCE="NONE"
            if minerva.should_sample(analysis_cycle):
                minerva.drop_batch("CPM", "EMPTY BUFFER - NO VALID FRAMES OR MISSED DEADLINE")
            message = f"RECEIVED EMPTY BUFFER FROM VIDEO SOURCE"
            most_common_landmark = 'NO_LANDMARK'
            logger.main('cpm', message)
        scheduler.signals.vai_return.wait()
        flags.VAI_arrived=False
        if FRAMES:
            try:
                C2V.put(FRAMES.copy(),block=False)
                FRAMES.clear()
            except multiprocessing.queues.Full:
                FRAMES.clear()
            while scheduler.signals.vai_return.is_set():
                try:
                    res=V2C.get(timeout=0.01)
                    vlabels=res['LABELS']
                    vac=res['AVG_CONF']
                    flags.VAI_arrived=True
                    message = f"RECEIVED SPREAD FROM VAI OF {vlabels} WITH AVERAGES {vac}"
                    logger.main('cpm', message)
                    if minerva.should_sample(analysis_cycle):
                        vai_peak_conf = max(vac)
                        vai_peak_mood = vlabels[vac.index(vai_peak_conf)]
                        minerva.store_video_result({"vai_mood" : vai_peak_mood, "vai_score" : vai_peak_conf})
                except multiprocessing.queues.Empty:
                    continue
        if not flags.VAI_arrived or np.sum(vac) == 0:
            vlabels,vac,most_common_landmark=None,0,'NO_LANDMARK'
            if minerva.should_sample(analysis_cycle):
                minerva.drop_batch("CPM", "NONE VAI RESULT, NO VALID FRAMES OR SCHEDULE MISSED")
            message = f"RECEIVED NONE VAI RESULT. BUFFER EMPTY OR SCHEDULE MISSED"
            logger.main('cpm', message)
        scheduler.signals.audio_arrive.wait()
        flags.audio_arrived=False
        latest_audio_pkt=None
        while scheduler.signals.audio_arrive.is_set():
            try:
                latest_audio_pkt=AC2C.get(timeout=0.01)
            except queue.Empty:
                continue
        if latest_audio_pkt is not None and latest_audio_pkt['BUFFER'] is not None:
            AUDIO_BUFFER_SOURCE=SOURCE(latest_audio_pkt['SOURCE']).name
            for a in latest_audio_pkt['BUFFER']:
                AUDIOS.append(a['AUDIO'])
            flags.audio_arrived=True
            message = f"RECEIVED BUFFER FROM SOURCE {AUDIO_BUFFER_SOURCE} OF SIZE {len(latest_audio_pkt['BUFFER'])}"
            logger.main('cpm', message)
            message = f"BUFFER HAS ID {latest_audio_pkt['BATCH']} CONTAINING AUDIO ID(S) {', '.join(str(p['ID']) for p in latest_audio_pkt['BUFFER'])}"
            logger.main('cpm', message)
        else:
            AUDIO_BUFFER_SOURCE="NONE"
            message = f"RECEIVED EMPTY BUFFER FROM AUDIO SOURCE"
            logger.main('cpm', message)
        scheduler.signals.aai_return.wait()
        flags.AAI_arrived=False
        if AUDIOS:
            try:
                C2A.put(AUDIOS.copy(),block=False)
                AUDIOS.clear()
            except multiprocessing.queues.Full:
                AUDIOS.clear()
            while scheduler.signals.aai_return.is_set():
                try:
                    res=A2C.get(timeout=0.01)
                    alabels=res['LABELS']
                    aac=res['AVG_CONF']
                    flags.AAI_arrived=True
                    message = f"RECEIVED SPREAD FROM AAI OF {alabels} WITH AVERAGES {aac}"
                    logger.main('cpm', message)
                except multiprocessing.queues.Empty:
                    continue
        if not flags.AAI_arrived or np.sum(vac) == 0:
            alabels,aac=None,0
            message = f"RECEIVED NONE AAI RESULT. BUFFER EMPTY OR SCHEDULE MISSED"
            logger.main('cpm', message)
        if vlabels is None: vac=0
        if alabels is None: aac=0
        mood,confidence,source=fusion(vlabels,alabels,vac,aac)
        if mood == 0:
            if minerva.should_sample(analysis_cycle):
                minerva.drop_batch("CPM", "FUSED RESULT RETURNED 0")
        else:
            if minerva.should_sample(analysis_cycle):
                minerva.store_fused_result({'fused_mood' : mood, 'fused_score' : confidence, 'source' : source})
                committed = minerva.commit_data()
                if not committed:
                    logger.main('cpm', 'MINERVA COMMIT FAILED AFTER FUSED RESULT')
        pkt={'VSOURCE':VIDEO_BUFFER_SOURCE,'ASOURCE':AUDIO_BUFFER_SOURCE,'MOOD':mood,'CONFIDENCE':confidence,'LANDMARK':most_common_landmark}
        try:
            C2D.put(pkt,block=False)
            message = f"SENDING PACKET {pkt} TO DISPATCHER"
            logger.main('cpm', message)
        except queue.Full:
            continue
    clean_up()

if __name__=="__main__":
    multiprocessing.freeze_support()
    main()