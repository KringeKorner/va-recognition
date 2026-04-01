# imports
from contextlib import redirect_stdout, redirect_stderr
from debug import logger
from funasr import AutoModel
from multiprocessing import Event, Process
from multiprocessing.queues import Full, Empty
from pathlib import Path
import numpy as np
import time
# TEMP
import sys, os, io

#vars
EMOTION_ORDER = [
    "angry",
    "disgust",
    "fear",
    "happy",
    "sad",
    "surprise",
    "neutral"
]
LABEL_MAP = {
    "angry": "angry",
    "disgusted": "disgust",
    "fearful": "fear",
    "happy": "happy",
    "neutral": "neutral",
    "sad": "sad",
    "surprised": "surprise",
    "other": "other"
}
EMOTIONS = []
RESULTS = []
RTFS = []
root_path = Path(__file__).resolve().parent.parent.parent.parent
sample_path = Path(root_path) / 'databases' / 'recording_tests' / 'sample_1.wav'

# helper functions
def initialize(C2A, A2C, AAI_HALT, AAI_READY):
    global AAI
    logger.main('system', "STARTING AAI")
    logger.main('aai', "STARTING AAI")
    AAI = Process(target=main, args=(C2A, A2C, AAI_HALT, AAI_READY), daemon=False, name="aai")
    AAI.start()

def clean_up(C2A, AAI_HALT):
    logger.main('system', "SHUTTING DOWN AAI")
    logger.main('aai', "SHUTTING DOWN AAI")
    AAI_HALT.set()
    AAI.join()
    while not C2A.empty():
        try:
            _ = C2A.get_nowait()
        except Empty:
            break
    logger.main('system', "AAI TERMINATED")
    logger.main('aai', "AAI TERMINATED")

def normalize_aai(labels, scores):
    mapped = {}
    for lbl, score in zip(labels, scores):
        new_lbl = LABEL_MAP[lbl]
        if new_lbl == "other":
            continue
        mapped[new_lbl] = score
    ordered_scores = [mapped[e] for e in EMOTION_ORDER]
    return EMOTION_ORDER, ordered_scores

def average(emotion_spread):
    labels = emotion_spread[0][0]
    scores_array = np.array([s[1] for s in emotion_spread])
    avg_scores = np.round(np.mean(scores_array, axis=0), 3).tolist()
    RESULT = {
        'LABELS' : labels,
        'AVG_CONF' : avg_scores
    }
    message = f"FOR {len(emotion_spread)} SAMPLES PRODUCED AVERAGING RESULT OF {labels} WITH SCORES {avg_scores}"
    logger.main('aai', message)
    return RESULT

def generate_silent(model, audio):
    f = io.StringIO()
    with redirect_stdout(f), redirect_stderr(f):
        result = model.generate(
            audio,
            granularity="utterance",
            extract_embedding=False,
        )
    return result

# main
def main(C2A, A2C, AAI_HALT, AAI_READY):
    logger.main('system', "INITIATING AAI WARMUP SEQUENCE")
    logger.main('aai', "INITIATING AAI WARMUP SEQUENCE")
    SER = AutoModel(
        model = "emotion2vec_plus_large",
        disable_update = True,
    )
    result = SER.generate(
        str(sample_path),
        granularity="utterance",
        extract_embedding=False,
    )
    AAI_READY.set()
    logger.main('system', "AAI ONLINE")
    logger.main('aai', "AAI ONLINE")
    while not AAI_HALT.is_set():
        try:
            AUDIOS = C2A.get(timeout=0.2)
            if not AUDIOS:
                continue
            message = f"RECEIVED {len(AUDIOS)} FOR AAI ANALYSIS"
            logger.main('aai', message)
            for i, AUDIO in enumerate(AUDIOS, start=1):
                result = generate_silent(SER, AUDIO)
                labels = [lbl.split('/')[-1] for lbl in result[0]['labels']]
                labels.pop()
                scores = [float(score*100) for score in result[0]['scores']]
                scores.pop()
                labels, scores = normalize_aai(labels, scores)
                message = f"FOR AUDIO SAMPLE {i} of {len(AUDIOS)} PRODUCED LOCAL RESULT {labels} WITH SCORES {scores}"
                logger.main('aai', message)
                EMOTIONS.append([labels, scores])
            RESULT = average(EMOTIONS)
            EMOTIONS.clear()
            try:
                A2C.put(RESULT, timeout=0.2)
            except Full:
                continue
        except Empty:
            continue