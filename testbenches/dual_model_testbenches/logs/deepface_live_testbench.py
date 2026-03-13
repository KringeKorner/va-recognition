from imutils.video import VideoStream as vs
from pathlib import Path
from deepface import DeepFace
import time
import cv2
from pynput import keyboard

# vars
CAM_SRC = 0
# CAM_RES = (640, 480)
CAM_RES = (1280, 720)
FRAME_RATE = 30

# setting up arcface
Model = "ArcFace"   # <-- ArcFace model
root_path = Path(__file__).resolve().parent.parent / 'dual_model_demo'
print(root_path)
frame_path = root_path / 'frame_db' / 'a1.jpg'
DB_PATH = root_path / 'database'
DETECTOR_BACKEND = "opencv"
# FACE_DISTANCE_METRIC = "euclidean_12"
FACE_DISTANCE_METRIC = "cosine"

 # ---- Warmup using ArcFace (do NOT crash if DB is empty) ----

results = DeepFace.find(
    img_path=frame_path,
    db_path=DB_PATH,
    model_name=Model,
    distance_metric=FACE_DISTANCE_METRIC,
    enforce_detection=False
)

STREAM = vs(src=CAM_SRC, resolution=CAM_RES, framerate=FRAME_RATE).start()

while True:
    frame = STREAM.read()
    if frame is None:
        raise FileNotFoundError(f"Image not found at path: {frame}")

    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # print("Running DeepFace analysis...")
    time_start = time.perf_counter()
    results = DeepFace.analyze(
        img_path=img_rgb,  # you can also pass the numpy array
        actions=['emotion'],
        enforce_detection=False  # prevents crash if face not detected perfectly
    )

    time_end = time.perf_counter()
    duration = time_end - time_start

    # print("\nDeepFace Analysis Results:")
    for face in results:
        emotion_detected = face['dominant_emotion']
        confidence = face['emotion'][emotion_detected]
        # print(f"Emotion: {emotion_detected} ({confidence:.2f}%) with duration ({duration:.3f}s)")

    label = f"{emotion_detected}: {confidence:.2f}%"
    cv2.putText(
        frame,
        label,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )
    label = f"{duration:.3f}s"
    cv2.putText(
        frame,
        label,
        (10, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA
    )

    cv2.imshow("Frame", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        break

cv2.destroyAllWindows()
vs.stop()
