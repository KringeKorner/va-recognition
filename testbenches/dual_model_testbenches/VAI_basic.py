# imports
from deepface import DeepFace
from multiprocessing import Event, Process
import cv2
import os
import time

# vars
loop_count = 0
VAI_TEST_THREAD = None
VAI_HALT = Event()

# helper functions
def write_to_file(log_path, message):
    with open(log_path, "a") as FILE:
        FILE.write(message)

def initialize(frame_path, log_path, VAI_READY, START):
    global VAI_TEST_THREAD
    print("INITIALIZING VAI")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} | INITIALIZING VAI\n---------------------------------------------\n"
    write_to_file(log_path, message)
    VAI_TEST_THREAD = Process(target=main, args=(frame_path, log_path, VAI_READY, START,), daemon=False)
    VAI_TEST_THREAD.start()

def cleanup(log_path):
    print('SHUTTING DOWN VAI')
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} | SHUTTING DOWN VAI\n---------------------------------------------\n"
    write_to_file(log_path, message)
    VAI_HALT.set()
    if VAI_TEST_THREAD.is_alive():
        VAI_TEST_THREAD.terminate()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} | VAI TERMINATED\n---------------------------------------------\n"
    write_to_file(log_path, message)

# main
def main(frame_path, log_path, VAI_READY, START):
    item_total = len(os.listdir(frame_path))
    global loop_count, VAI_HALT
    print("RUNNING WARMUP STAGE")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} | RUNNING VAI WARMUP\n---------------------------------------------\n"
    write_to_file(log_path, message)
    img = cv2.imread(next(frame_path.glob('*.jpg'), None))
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = DeepFace.analyze(
        img_path=img_rgb,
        actions=['emotion'],
        enforce_detection=False
    )
    VAI_READY.set()
    START.wait()
    while not VAI_HALT.is_set():
        loop_count += 1
        count = 0
        for frame in frame_path.glob('*.jpg'):
            if not VAI_HALT.is_set():
                count += 1
                img = cv2.imread(frame)
                if img is None:
                    raise FileNotFoundError(f"Image not found at path: {frame}")
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                time_start = time.perf_counter()
                results = DeepFace.analyze(
                    img_path=img_rgb,
                    actions=['emotion'],
                    enforce_detection=False
                )
                time_end = time.perf_counter()
                duration = round((time_end - time_start), 3)
                for face in results:
                    emotion_detected = face['dominant_emotion']
                    confidence = round(float(face['emotion'][emotion_detected]), 3)
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    message = f"{timestamp} | VAI | Produced results:\nEmotion: {emotion_detected}, confidence: {confidence} in {duration}s\nItem {count} of {item_total}\n---------------------------------------------\n"
                    write_to_file(log_path, message)