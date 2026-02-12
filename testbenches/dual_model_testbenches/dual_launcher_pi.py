# from pathlib import Path
# import AAI_basic, VAI_basic
# import multiprocessing
# import time
# import signal
# import sys
# from pynput import keyboard

# root_path = Path(__file__).resolve().parent
# audio_path = root_path / 'audio_db'
# frame_path = root_path / 'frame_db'
# log_path = root_path / 'logs' / 'DUAL_MODEL_LOG.txt'
# VAI_READY = multiprocessing.Event()
# AAI_READY = multiprocessing.Event()
# START = multiprocessing.Event()
# STOP = False

# # Helper functions
# def write_to_file(log_path, message):
#     with open(log_path, "a") as FILE:
#         FILE.write(message)

# def signal_handler(sig, frame):
#     global STOP
#     STOP = True
#     VAI_basic.cleanup(log_path)
#     AAI_basic.cleanup(log_path)
#     sys.exit(0)

# def on_key_press(key):
#     global STOP
#     try:
#         if key.char == 'q':
#             STOP = True
#             return False
#     except AttributeError:
#         pass

# def main():
#     log_path.parent.mkdir(parents=True, exist_ok=True)
#     with open(log_path, "w") as FILE:
#         FILE.write("DEMO PROGRAM TO RUN PARALLEL AI.\nPOC TEST ONLY, ACCURACY NOT TESTED.\n---------------------------------------------\n")
#     AAI_basic.initialize(audio_path, log_path, AAI_READY, START)
#     VAI_basic.initialize(frame_path, log_path, VAI_READY, START)
#     print("WAITING ON MODEL READY")
#     timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
#     write_to_file(log_path, f"{timestamp} | WAITING ON MODEL READY\n---------------------------------------------\n")
#     AAI_READY.wait()
#     VAI_READY.wait()
#     print("MODELS READY, LAUNCHING")
#     timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
#     write_to_file(log_path, f"{timestamp} | LAUNCHING MODELS\n---------------------------------------------\n")
#     START.set()
#     listener = keyboard.Listener(on_press=on_key_press)
#     listener.start()
#     while not STOP:
#         time.sleep(0.1)
#     print("SHUTTING DOWN TEST PROGRAM")
#     VAI_basic.cleanup(log_path)
#     AAI_basic.cleanup(log_path)
#     print("SHUTDOWN SUCCESSFUL, EXITING")

# if __name__ == "__main__":
#     signal.signal(signal.SIGINT, signal_handler)
#     main()