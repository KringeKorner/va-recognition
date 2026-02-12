# imports
from contextlib import redirect_stdout, redirect_stderr
from funasr import AutoModel
from multiprocessing import Event, Process
import io
import os
import time

# vars
AAI_HALT = Event()
AAI_TEST_THREAD = None
loop_count = 0

# helper functions
def write_to_file(log_path, message):
    with open(log_path, "a") as FILE:
        FILE.write(message)

def initialize(audio_path, log_path, AAI_READY, START):
    global AAI_TEST_THREAD
    print("INITIALIZING AAI")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} | INITIALIZING AAI\n---------------------------------------------\n"
    write_to_file(log_path, message)
    AAI_TEST_THREAD = Process(target=main, args=(audio_path, log_path, AAI_READY, START,), daemon=False)
    AAI_TEST_THREAD.start()

def cleanup(log_path):
    print('SHUTTING DOWN AAI')
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} | SHUTTING DOWN AAI\n---------------------------------------------\n"
    write_to_file(log_path, message)
    AAI_HALT.set()
    if AAI_TEST_THREAD.is_alive():
        AAI_TEST_THREAD.terminate()
    print("AAI TERMINATED")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} | AAI TERMINATED\n---------------------------------------------\n"
    write_to_file(log_path, message)

# main
def main(audio_path, log_path, AAI_READY, START):
    item_total = len(os.listdir(audio_path))
    SER = AutoModel(
        model = "emotion2vec_plus_large",
        disable_update = True
    )
    global loop_count, AAI_HALT
    print("RUNNING WARMUP STAGE")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} | RUNNING AAI WARMUP\n---------------------------------------------\n"
    write_to_file(log_path, message)
    audio = str(next(audio_path.glob('*.wav'), None))
    f = io.StringIO()
    with redirect_stdout(f), redirect_stderr(f):
        result = SER.generate(
            str(audio),
            granularity="utterance",
            extract_embedding=False,
            fs = 16000
        )
    AAI_READY.set()
    START.wait()
    while not AAI_HALT.is_set():
        loop_count += 1
        count = 0
        for audio in audio_path.glob('*.wav'):
            if not AAI_HALT.is_set():
                count += 1
                time_start = time.perf_counter()
                f = io.StringIO()
                with redirect_stdout(f), redirect_stderr(f):
                    result = SER.generate(
                        str(audio),
                        granularity="utterance",
                        extract_embedding=False,
                        fs = 16000
                    )
                time_end = time.perf_counter()
                duration = round((time_end - time_start), 3)
                labels = [lbl.split('/')[-1] for lbl in result[0]['labels']]
                labels.pop()
                scores = [round(score, 3) for score in result[0]['scores']]
                scores.pop()
                confidence = max(scores)
                emotion = labels[scores.index(confidence)]
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                message = f"{timestamp} | AAI | Produced results:\nEmotion: {emotion}, confidence: {confidence} in {duration}s\nItem {count} of {item_total}\n---------------------------------------------\n"
                write_to_file(log_path, message)
