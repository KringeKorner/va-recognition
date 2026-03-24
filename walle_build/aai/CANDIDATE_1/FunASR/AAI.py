from contextlib import redirect_stdout, redirect_stderr
from funasr import AutoModel
from multiprocessing import Event, Process
from multiprocessing.queues import Full, Empty
from pathlib import Path
import numpy as np
import time
import os
import io

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

root_path = Path(__file__).resolve().parents[3]
sample_path = root_path / "databases" / "recording_tests" / "sample_1.wav"
DEVNULL = open(os.devnull, "w")

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


def normalize_aai(labels, scores):
    mapped = {}
    for lbl, score in zip(labels, scores):
        new_lbl = LABEL_MAP.get(lbl, "other")
        if new_lbl == "other":
            continue
        mapped[new_lbl] = score
    ordered_scores = [mapped.get(e, 0.0) for e in EMOTION_ORDER]
    return EMOTION_ORDER, ordered_scores

def average(emotion_spread):
    labels = emotion_spread[0][0]
    scores_array = np.array([s[1] for s in emotion_spread])
    avg_scores = np.round(np.mean(scores_array, axis=0), 3).tolist()
    RESULT = {
        "LABELS": labels,
        "AVG_CONF": avg_scores
    }
    return RESULT


def generate_silent(model, audio):
    with redirect_stdout(DEVNULL), redirect_stderr(DEVNULL):
        result = model.generate(
            audio,
            granularity="utterance",
            extract_embedding=False,
        )
    return result


def main(C2A, A2C, AAI_HALT, AAI_READY):
    print("INITIATING AAI WARMUP SEQUENCE")

    if not sample_path.exists():
        raise FileNotFoundError(f"AAI warmup sample missing: {sample_path}")
    SER = AutoModel(
        model="emotion2vec_plus_large",
        disable_update=True,
    )
    SER.generate(
        str(sample_path),
        granularity="utterance",
        extract_embedding=False,
    )
    AAI_READY.set()
    print("AAI ONLINE\n")
    EMOTIONS = []
    while not AAI_HALT.is_set():
        try:
            AUDIOS = C2A.get(timeout=0.2)
            if not AUDIOS:
                continue
            for AUDIO in AUDIOS:
                result = generate_silent(SER, AUDIO)
                labels = [lbl.split("/")[-1] for lbl in result[0]["labels"]]
                labels.pop()
                scores = [float(score * 100) for score in result[0]["scores"]]
                scores.pop()
                labels, scores = normalize_aai(labels, scores)
                EMOTIONS.append([labels, scores])
            RESULT = average(EMOTIONS)
            EMOTIONS.clear()
            try:
                A2C.put(RESULT, timeout=0.2)
            except Full:
                continue
        except Empty:
            continue