from deepface import DeepFace
from pathlib import Path
import cv2
import time

#paths
ROOT_PATH = Path(__file__).resolve().parent
img_path = Path(ROOT_PATH) / "img1.png"
TEST_DB = Path(ROOT_PATH).parent.parent / 'databases' / 'sample_db'

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
        emotion_detected = face['dominant_emotion']
        confidence = face['emotion'][emotion_detected]
        print(f"Emotion: {emotion_detected} ({confidence:.2f}%) with duration ({duration:.3f}s)")

# print(results)