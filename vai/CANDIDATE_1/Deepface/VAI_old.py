# imports
from collections import defaultdict, Counter
from debug import logger
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
    logger.main('system', "STARTING VAI")
    logger.main('vai', "STARTING VAI")
    VAI = Process(target=main, args=(C2V,V2C,VAI_HALT,VAI_READY), daemon=False, name="vai")
    VAI.start()

def average(emotion_spread):
    labels = emotion_spread[0][0]
    scores_array = np.array([s[1] for s in emotion_spread])
    avg_scores = np.round(np.mean(scores_array, axis=0), 3).tolist()
    RESULT = {
        'LABELS' : labels,
        'AVG_CONF' : avg_scores
    }
    message = f"FOR {len(emotion_spread)} SAMPLES PRODUCED AVERAGING RESULT OF {labels} WITH SCORES {avg_scores}"
    logger.main('vai', message)
    return RESULT

def clean_up(C2V, VAI_HALT):
    logger.main('system', "SHUTTING DOWN VAI")
    logger.main('vai', "SHUTTING DOWN VAI")
    VAI_HALT.set()
    VAI.join()
    while not C2V.empty():
        try:
            _ = C2V.get_nowait()
        except Empty:
            break
    logger.main('system', "VAI TERMINATED")
    logger.main('vai', "VAI TERMINATED")

# main
def main(C2V, V2C, VAI_HALT, VAI_READY):
    logger.main('system', "INITIATING VAI WARMUP SEQUENCE")
    logger.main('vai', "INITIATING VAI WARMUP SEQUENCE")
    DeepFace.analyze(
        img_path=np.zeros((224, 224, 3), dtype=np.uint8),
        actions=['emotion'],
        enforce_detection=False
    )
    VAI_READY.set()
    logger.main('system', "VAI ONLINE")
    logger.main('vai', "VAI ONLINE")
    while not VAI_HALT.is_set():
        try:
            FRAMES = C2V.get(timeout=0.2)
            if not FRAMES:
                continue
            message = f"RECEIVED {len(FRAMES)} FOR VAI ANALYSIS"
            logger.main('vai', message)
            for i, FRAME in enumerate(FRAMES, start=1):
                img_rgb = cv2.cvtColor(FRAME, cv2.COLOR_BGR2RGB)
                results = DeepFace.analyze(
                    img_path=img_rgb,
                    actions=['emotion'],
                    enforce_detection=False
                )
                for face in results:
                    emotions = face['emotion']
                    labels = list(emotions.keys())
                    scores = [float(v) for v in emotions.values()]
                    message = f"FOR FRAME {i} of {len(FRAMES)} PRODUCED LOCAL RESULT {labels} WITH SCORES {scores}"
                    logger.main('vai', message)
                    EMOTIONS.append([labels, scores])
            result = average(EMOTIONS)
            EMOTIONS.clear()
            try:
                V2C.put(result, timeout=0.2)
            except Full:
                continue
        except Empty:
            continue
