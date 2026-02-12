# imports
# TEMP
from contextlib import redirect_stdout, redirect_stderr
from funasr import AutoModel
from multiprocessing import Event, Process
from multiprocessing.queues import Full, Empty
from pathlib import Path
import numpy as np
import time
# TEMP
import sys, os, io

#vars
EMOTIONS = []
RESULTS = []
RTFS = []
root_path = Path(__file__).resolve().parent.parent.parent.parent
sample_path = Path(root_path) / 'databases' / 'recording_tests' / 'sample_1.wav'

# helper functions
def initialize(C2A, A2C, AAI_HALT, AAI_READY):
    global AAI
    print("STARTING AAI")
    AAI = Process(target=main, args=(C2A, A2C, AAI_HALT, AAI_READY), daemon=False)
    AAI.start()

def clean_up(C2A, AAI_HALT):
    print("SHUTTING DOWN AAI")
    AAI_HALT.set()
    AAI.join()
    while not C2A.empty():
        try:
            _ = C2A.get_nowait()
        except Empty:
            break
    print("AAI TERMINATED")

def average(emotion_spread):
    labels = emotion_spread[0][0]
    scores_array = np.array([s[1] for s in emotion_spread])
    avg_scores = np.mean(scores_array, axis=0)
    max_index = np.argmax(avg_scores)
    RESULT = {
        'EMOTION' : labels[max_index],
        'AVG_CONF' : round(avg_scores[max_index], 3),
        'LABELS' : labels
    }
    return RESULT

# TEMP, TO BE REMOVED
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
    print("INITIATING AAI WARMUP SEQUENCE")
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
    print("AAI ONLINE\n")
    while not AAI_HALT.is_set():
        try:
            AUDIOS = C2A.get(timeout=0.2)
            if not AUDIOS:
                continue
            for AUDIO in AUDIOS:
                # result = SER.generate(
                #     AUDIO,
                #     granularity="utterance",
                #     extract_embedding=False,
                # )
                result = generate_silent(SER, AUDIO)
                labels = [lbl.split('/')[-1] for lbl in result[0]['labels']]
                labels.pop()
                scores = [round(score, 3) for score in result[0]['scores']]
                scores.pop()
                EMOTIONS.append([labels, scores])
            RESULT = average(EMOTIONS)
            EMOTIONS.clear()
            try:
                A2C.put(RESULT, timeout=0.2)
            except Full:
                continue
        except Empty:
            continue