from pathlib import Path
import datetime
import time

root_path = Path(__file__).resolve().parent
runs_path = root_path / "runs"
current_run = None

# files
log_files = {
    'system': {'folder': 'system_logs', 'file': 'system_log'},
    'MINERVA': {'folder': 'MINERVA_logs', 'file': 'MINERVA_log'},
    'scheduler': {'folder': 'scheduler_logs', 'file': 'scheduler_log'},
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
def get_global_run_number():
    global current_run
    date = datetime.datetime.now().strftime("%d_%m_%Y")
    runs_path.mkdir(parents=True, exist_ok=True)
    run_file = runs_path / f"{date}_run.txt"
    if not run_file.exists():
        run_number = 1
    else:
        try:
            with open(run_file, "r") as f:
                run_number = int(f.read().strip()) + 1
        except:
            run_number = 1
    with open(run_file, "w") as f:
        f.write(str(run_number))
    current_run = f"R{run_number:02d}"
    
def read_current_run_number():
    global current_run
    if current_run is not None:
        return current_run
    date = datetime.datetime.now().strftime("%d_%m_%Y")
    run_file = runs_path / f"{date}_run.txt"
    if run_file.exists():
        try:
            with open(run_file, "r") as f:
                run_number = int(f.read().strip())
            current_run = f"R{run_number:02d}"
            return current_run
        except:
            pass
    return "R01"

def path_formatter(source):
    date = datetime.datetime.now().strftime("%d_%m_%Y")
    group = log_files[source]
    folder = group['folder']
    file = group['file']
    daily_folder_name = f"{file}_{date}_logs"
    daily_folder_path = root_path / folder / daily_folder_name
    run_number = read_current_run_number()
    file_name = f"{run_number}_{file}_{date}_log.txt"
    file_path = daily_folder_path / file_name
    return file_path

def log(path, message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    separator = '-' * 100
    file_message = f"{timestamp} | {message}\n{separator}\n"
    with open(path, "a") as FILE:
        FILE.write(file_message)

def initialize():
    global current_run
    if current_run is None:
        get_global_run_number()
    for system in log_files:
        path = path_formatter(system)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.stat().st_size == 0:
            with open(path, "a") as FILE:
                FILE.write("----------------------------------------------------------------------------------------------------\n")
            file_message = f"CONFIGURING {system.upper()} LOG FILE ({current_run})"
            log(path, file_message)

# main
def main(source, message):
    path = path_formatter(source)
    log(path, message)