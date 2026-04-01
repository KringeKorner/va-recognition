# imports
from collections import defaultdict, Counter
from debug import logger
from deepface import DeepFace
from multiprocessing import Event, Process
from multiprocessing.queues import Full, Empty
import cv2
import numpy as np
import os

#vars
EMOTIONS = []
IDENTITIES = []

# ArcFace recognition settings
MODEL_NAME = "ArcFace"
DISTANCE_METRIC = "cosine"
DETECTOR_BACKEND = "opencv"
ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT_PATH, "database")

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

    # ArcFace warmup
    try:
        if os.path.isdir(DB_PATH) and any(os.scandir(DB_PATH)):
            DeepFace.find(
                img_path=np.zeros((224, 224, 3), dtype=np.uint8),
                db_path=DB_PATH,
                model_name=MODEL_NAME,
                distance_metric=DISTANCE_METRIC,
                enforce_detection=False,
                detector_backend=DETECTOR_BACKEND
            )
    except Exception as e:
        logger.main('vai', f"ARCFACE WARMUP SKIPPED: {e}")

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

                # Emotion analysis
                results = DeepFace.analyze(
                    img_path=img_rgb,
                    actions=['emotion'],
                    enforce_detection=False
                )

                # ArcFace recognition
                identity_name = "N/A"
                identity_conf = 0.0
                try:
                    if os.path.isdir(DB_PATH) and any(os.scandir(DB_PATH)):
                        find_results = DeepFace.find(
                            img_path=img_rgb,
                            db_path=DB_PATH,
                            model_name=MODEL_NAME,
                            distance_metric=DISTANCE_METRIC,
                            enforce_detection=False,
                            detector_backend=DETECTOR_BACKEND
                        )
                        if isinstance(find_results, list) and len(find_results) > 0 and not find_results[0].empty:
                            identity = find_results[0].iloc[0]["identity"]
                            dist = float(find_results[0].iloc[0]["distance"])
                            identity_name = identity.replace("\\", "/").split("/")[-1].split(".")[0]
                            identity_conf = max(0.0, 100.0 - dist * 100.0)
                except Exception as e:
                    logger.main('vai', f"FOR FRAME {i} RECOGNITION FAILED: {e}")

                IDENTITIES.append((identity_name, identity_conf))

                for face in results:
                    emotions = face['emotion']
                    labels = list(emotions.keys())
                    scores = [float(v) for v in emotions.values()]
                    message = f"FOR FRAME {i} of {len(FRAMES)} PRODUCED LOCAL RESULT {labels} WITH SCORES {scores}"
                    logger.main('vai', message)
                    EMOTIONS.append([labels, scores])

            result = average(EMOTIONS)

            # choose most common identity in batch, then highest confidence among that identity
            if IDENTITIES:
                names = [x[0] for x in IDENTITIES if x[0] != "N/A"]
                if names:
                    most_common_name = Counter(names).most_common(1)[0][0]
                    matching_scores = [conf for name, conf in IDENTITIES if name == most_common_name]
                    result["IDENTITY"] = most_common_name
                    result["ID_CONF"] = round(max(matching_scores), 3) if matching_scores else 0.0
                else:
                    result["IDENTITY"] = "N/A"
                    result["ID_CONF"] = 0.0
            else:
                result["IDENTITY"] = "N/A"
                result["ID_CONF"] = 0.0

            EMOTIONS.clear()
            IDENTITIES.clear()

            try:
                V2C.put(result, timeout=0.2)
            except Full:
                continue
        except Empty:
            continue
