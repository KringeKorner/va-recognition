from deepface import DeepFace
from pathlib import Path
import cv2
import numpy as np
import time

#paths
ROOT_PATH = Path(__file__).resolve().parent
img_path = Path(ROOT_PATH) / "img1.png"
TEST_DB = Path(ROOT_PATH).parent.parent / 'databases' / 'sample_db'

EMOTIONS = []

def average(emotion_spread):
    labels = emotion_spread[0][0]
    scores_array = np.array([s[1] for s in emotion_spread])
    avg_scores = np.mean(scores_array, axis=0)
    max_index = np.argmax(avg_scores)
    RESULT = {
        'EMOTION' : labels[max_index],
        'AVG_CONF' : round(float(avg_scores[max_index]), 3),
        'LABELS' : labels
    }
    return RESULT

for img_path in TEST_DB.glob('*.jpg'):

    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"Image not found at path: {img_path}")

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    print("Running DeepFace analysis...")
    time_start = time.perf_counter()
    results = DeepFace.analyze(
        img_path=img_rgb,  # you can also pass the numpy array
        actions=['emotion'],
        enforce_detection=False  # prevents crash if face not detected perfectly
    )

    time_end = time.perf_counter()
    duration = time_end - time_start

    print("\nDeepFace Analysis Results:")
    for face in results:
        emotions = face['emotion']
        labels = list(emotions.keys())
        scores = [round(v, 3) for v in emotions.values()]
        EMOTIONS.append([labels, scores])
        result = average(EMOTIONS)
        EMOTIONS.clear()

        print(f"Returned {result['EMOTION']} with confidence {result['AVG_CONF']}% in {round(duration, 3)}s")