# imports
from pathlib import Path
import AAI_basic, VAI_basic
import keyboard
import multiprocessing
import time

# vars
root_path = Path(__file__).resolve().parent
audio_path = Path(root_path) / 'audio_db'
frame_path = Path(root_path) / 'frame_db'
log_path = Path(root_path) / 'logs' / 'DUAL_MODEL_LOG.txt'
VAI_READY = multiprocessing.Event()
AAI_READY = multiprocessing.Event()
START = multiprocessing.Event()

# helper functions
def write_to_file(log_path, message):
    with open(log_path, "a") as FILE:
        FILE.write(message)

# main
def main():
    with open(log_path, "w") as FILE:
            FILE.write("")
    with open(log_path, "a") as FILE:
            FILE.write("DEMO PROGRAM TO RUN PARALLEL AI.\nPOC TEST ONLY, ACCURACY NOT TESTED.\n---------------------------------------------\n")
    AAI_basic.initialize(audio_path, log_path, AAI_READY, START)
    VAI_basic.initialize(frame_path, log_path, VAI_READY, START)
    print("WAITING ON MODEL READY")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} | WAITING ON MODEL READY\n---------------------------------------------\n"
    write_to_file(log_path, message)
    AAI_READY.wait()
    VAI_READY.wait()
    print("MODELS READY, LAUNCHING")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} | LAUNCHING MODELS\n---------------------------------------------\n"
    write_to_file(log_path, message)
    START.set()
    while True:
        if keyboard.is_pressed('q'):
            print("SHUTTING DOWN TEST PROGRAM")
            VAI_basic.cleanup(log_path)
            AAI_basic.cleanup(log_path)
            print("SHUTDOWN SUCCESSFUL, EXITING")
            break
        time.sleep(0.1)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()