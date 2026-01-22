# imports
from collections import defaultdict, Counter
from deepface import DeepFace
from multiprocessing import Event, Process
from multiprocessing.queues import Full, Empty
import cv2
import numpy as np

#vars
EMOTIONS = []

# helper functions
def initialize(C2V, V2C, VAI_HALT, VAI_READY):
    global VAI
    print("STARTING VAI")
    VAI = Process(target=main, args=(C2V,V2C,VAI_HALT,VAI_READY), daemon=False)
    VAI.start()

def average(emotion_spread):
    # TODO: implement a way to decide tiebreaker case based on highest confidence rating
    t_confidence = defaultdict(float)
    counts = defaultdict(int)
    for e in emotion_spread:
        E = e['EMOTION']
        C = e['CONFIDENCE']
        t_confidence[E] += C
        counts[E] += 1
    peak = max(counts.items(), key=lambda x: x[1])[0]
    occurance = counts[peak]
    avg_c = round(float(t_confidence[peak]/occurance), 2)
    RESULT = {
        'EMOTION': peak,
        'AVG_CONF': avg_c,
        'OCCURANCE': occurance
    }
    return RESULT

def clean_up(C2V, VAI_HALT):
    print("SHUTTING DOWN VAI")
    VAI_HALT.set()
    VAI.join()
    while not C2V.empty():
        try:
            _ = C2V.get_nowait()
        except Empty:
            break
    print("VAI TERMINATED")

# main
def main(C2V, V2C, VAI_HALT, VAI_READY):
    print("INITIATING WARMUP SEQUENCE")
    DeepFace.analyze(
        img_path=np.zeros((224, 224, 3), dtype=np.uint8),
        actions=['emotion'],
        enforce_detection=False
    )
    VAI_READY.set()
    print("VAI ONLINE\n")
    while not VAI_HALT.is_set():
        try:
            FRAMES = C2V.get(timeout=0.2)
            if not FRAMES:
                continue
            for FRAME in FRAMES:
                img_rgb = cv2.cvtColor(FRAME, cv2.COLOR_BGR2RGB)
                results = DeepFace.analyze(
                    img_path=img_rgb,
                    actions=['emotion'],
                    enforce_detection=False
                )
                for face in results:
                    emotion_detected = face['dominant_emotion']
                    confidence = face['emotion'][emotion_detected]
                    RESULT = {
                        'EMOTION': emotion_detected,
                        'CONFIDENCE': confidence,
                    }
                EMOTIONS.append(RESULT)
            RESULT = average(EMOTIONS)
            EMOTIONS.clear()
            try:
                V2C.put(RESULT, timeout=0.2)
            except Full:
                continue
        except Empty:
            continue
