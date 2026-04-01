import os
import cv2
import numpy as np
from deepface import DeepFace
from multiprocessing import Process
from multiprocessing.queues import Empty, Full

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

VAI = None
LABELS = ["angry", "disgust", "fear", "happy", "sad", "surprise", "neutral"]
FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def zero_result():
    return {"LABELS": LABELS, "AVG_CONF": [0.0] * 7}

def average(emotion_spread):
    if not emotion_spread:
        return zero_result()
    return {"LABELS": LABELS, "AVG_CONF": np.round(np.mean([x[1] for x in emotion_spread], axis=0), 3).tolist()}

def initialize(C2V, V2C, VAI_HALT, VAI_READY):
    global VAI
    VAI = Process(target=main, args=(C2V, V2C, VAI_HALT, VAI_READY), daemon=False)
    VAI.start()

def clean_up(C2V, VAI_HALT):
    VAI_HALT.set()
    if VAI is not None:
        VAI.join(timeout=2.0)
        if VAI.is_alive():
            VAI.terminate()
    while not C2V.empty():
        try:
            C2V.get_nowait()
        except Empty:
            break

def main(C2V, V2C, VAI_HALT, VAI_READY):
    try:
        DeepFace.analyze(
            img_path=np.zeros((224, 224, 3), dtype=np.uint8),
            actions=["emotion"],
            enforce_detection=False,
            detector_backend="opencv"
        )
    except Exception:
        pass

    VAI_READY.set()

    while not VAI_HALT.is_set():
        try:
            frames = C2V.get(timeout=0.2)
        except Empty:
            continue

        if not frames or frames[-1] is None:
            try:
                V2C.put(zero_result(), timeout=0.2)
            except Full:
                pass
            continue

        frame = cv2.resize(frames[-1], (640, 360))
        if len(FACE_CASCADE.detectMultiScale(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 1.1, 5)) == 0:
            try:
                V2C.put(zero_result(), timeout=0.2)
            except Full:
                pass
            continue

        try:
            result = DeepFace.analyze(
                img_path=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                actions=["emotion"],
                enforce_detection=False,
                detector_backend="opencv"
            )
            face = result[0] if isinstance(result, list) and result else {}
            emotion = face.get("emotion", {})
            output = average([[LABELS, [float(emotion.get(label, 0.0)) for label in LABELS]]])
        except Exception:
            output = zero_result()

        try:
            V2C.put(output, timeout=0.2)
        except Full:
            pass