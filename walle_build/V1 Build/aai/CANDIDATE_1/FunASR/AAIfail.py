# imports
from contextlib import redirect_stdout, redirect_stderr
from funasr import AutoModel
from multiprocessing import Process
from multiprocessing.queues import Full, Empty
import numpy as np
import io
import os

# vars
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

# first-run / Pi-friendly config
MODEL_NAME = "emotion2vec_base_finetuned"
SAMPLE_RATE = 16000

AAI = None


# ------------------ HELPER FUNCTIONS ------------------
def initialize(C2A, A2C, AAI_HALT, AAI_READY):
    global AAI
    print("STARTING AAI")
    AAI = Process(target=main, args=(C2A, A2C, AAI_HALT, AAI_READY), daemon=False)
    AAI.start()

def clean_up(C2A, AAI_HALT):
    print("SHUTTING DOWN AAI")
    AAI_HALT.set()

    if AAI is not None:
        AAI.join(timeout=2.0)
        if AAI.is_alive():
            AAI.terminate()

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

    ordered_scores = [float(mapped.get(e, 0.0)) for e in EMOTION_ORDER]
    return EMOTION_ORDER, ordered_scores

def average(emotion_spread):
    if not emotion_spread:
        return {
            "LABELS": EMOTION_ORDER,
            "AVG_CONF": [0.0] * len(EMOTION_ORDER)
        }

    labels = emotion_spread[0][0]
    scores_array = np.array([s[1] for s in emotion_spread], dtype=np.float32)
    avg_scores = np.round(np.mean(scores_array, axis=0), 3).tolist()

    return {
        "LABELS": labels,
        "AVG_CONF": avg_scores
    }

def generate_silent(model, audio):
    """
    Suppresses FunASR stdout/stderr spam.
    Assumes CPM passes raw audio arrays or waveforms.
    """
    f = io.StringIO()
    with redirect_stdout(f), redirect_stderr(f):
        try:
            result = model.generate(
                input=audio,
                granularity="utterance",
                extract_embedding=False,
                fs=SAMPLE_RATE
            )
        except TypeError:
            result = model.generate(
                audio,
                granularity="utterance",
                extract_embedding=False,
                fs=SAMPLE_RATE
            )
    return result

def zero_result():
    return {
        "LABELS": EMOTION_ORDER,
        "AVG_CONF": [0.0] * len(EMOTION_ORDER)
    }


# ------------------ MAIN ------------------
def main(C2A, A2C, AAI_HALT, AAI_READY):
    print("INITIATING AAI WARMUP SEQUENCE")

    # First run on Pi: this may download the model automatically
    SER = AutoModel(
        model=MODEL_NAME,
        disable_update=True,
    )

    # Warmup using dummy audio instead of requiring a sample wav file
    try:
        dummy_audio = np.zeros(SAMPLE_RATE, dtype=np.float32)  # 1 second of silence
        _ = SER.generate(
            input=dummy_audio,
            granularity="utterance",
            extract_embedding=False,
            fs=SAMPLE_RATE
        )
    except Exception:
        pass

    AAI_READY.set()
    print("AAI ONLINE\n")

    while not AAI_HALT.is_set():
        try:
            AUDIOS = C2A.get(timeout=0.2)
        except Empty:
            continue

        if not AUDIOS:
            try:
                A2C.put(zero_result(), timeout=0.2)
            except Full:
                pass
            continue

        EMOTIONS = []

        for AUDIO in AUDIOS:
            try:
                result = generate_silent(SER, AUDIO)

                labels = [lbl.split("/")[-1] for lbl in result[0]["labels"]]
                scores = [float(score * 100.0) for score in result[0]["scores"]]

                # remove <unk> if present as last item
                if labels and labels[-1] == "<unk>":
                    labels.pop()
                    scores.pop()

                labels, scores = normalize_aai(labels, scores)
                EMOTIONS.append([labels, scores])

            except Exception:
                continue

        RESULT = average(EMOTIONS)

        try:
            A2C.put(RESULT, timeout=0.2)
        except Full:
            continue
