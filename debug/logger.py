# imports
from pathlib import Path
import datetime
import os
import time

# vars
root_path = Path(__file__).resolve().parent

# files
log_files = {
    'system': {'folder': 'system_logs', 'file': 'system_log'},
    'video_recorder': {'folder': 'video_recorder_logs', 'file': 'video_recorder_log'},
    'video_analyzer': {'folder': 'video_analyzer_logs', 'file': 'video_analyzer_log'},
    'video_controller': {'folder': 'video_controller_logs', 'file': 'video_controller_log'},
    'audio_recorder': {'folder': 'audio_recorder_logs', 'file': 'audio_recorder_log'},
    'audio_controller': {'folder': 'audio_controller_logs', 'file': 'audio_controller_log'},
    'cpm': {'folder': 'cpm_logs', 'file': 'cpm_log'},
    'dispatcher': {'folder': 'dispatcher_logs', 'file': 'dispatcher_log'},
    'vai': {'folder': 'vai_logs', 'file': 'vai_log'},
    'aai': {'folder': 'aai_logs', 'file': 'aai_log'},
}

# helper functions
def path_formatter(source):
    date = datetime.datetime.now().strftime("_%d_%m_%Y")
    group = log_files[source]
    folder = group['folder']
    file = group['file']
    file_name = "".join([file, date,'.txt'])
    file_path = root_path / folder / file_name
    return file_path

def log(path, message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    separator = '-' * 75
    file_message = f"{timestamp} | {message}\n{separator}\n"
    with open(path, "a") as FILE:
        FILE.write(file_message)

def initialize():
    for system in log_files:
        path = path_formatter(system)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.stat().st_size == 0:
            with open(path, "a") as FILE:
                FILE.write("---------------------------------------------------------------------------\n")
            file_message = f"CONFIGURING {system.upper()} LOG FILE"
            log(path, file_message)

# main
def main(source, message):
    path = path_formatter(source)
    log(path, message)