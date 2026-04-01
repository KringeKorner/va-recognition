# imports
from cpm import central_processing_module as CPM
from debug import logger
import threading
import time

# signals
class Signals:
    vc_start = threading.Event()
    ac_start = threading.Event()
    frames_arrive = threading.Event()
    vai_return = threading.Event()
    audio_arrive = threading.Event()
    aai_return = threading.Event()
signals = Signals()

# timings
class Schedule:
    frames_recording_start = 0.0
    audio_recording_start = 0.0
    frames_recording_stop = 1.0
    frames_arrival = 1.0
    vai_dispatch = 1.0
    vai_result = 3.0
    audio_recording_stop = 4.0
    aai_dispatch = 4.0
    aai_result = 5.0
schedules = Schedule()

# leniency
class Leniency:
    frames_leniency = 0.5
    vai_leniency = 1.0
    audio_leniency = 0.5
    aai_leniency = 0.5
leniencies = Leniency()

# vars
SCHEDULER_THREAD = None
SCHEDULER_HALT = threading.Event()

# helper functions
def initialize():
    global SCHEDULER_THREAD
    logger.main('system', 'INITIALIZING SCHEDUELER')
    logger.main('scheduler', 'INITIALIZING SCHEDUELER')
    SCHEDULER_THREAD = threading.Thread(target=main, args=(), daemon=False, name="scheduler")
    SCHEDULER_THREAD.start()

def clean_up():
    SCHEDULER_HALT.set()
    logger.main('system', 'SHUTTING DOWN SCHEDULER')
    logger.main('scheduler', 'SHUTTING DOWN SCHEDULER')
    if SCHEDULER_THREAD is not None:
        SCHEDULER_THREAD.join(timeout=2.0)
    logger.main('system', 'SCHEDULER TERMINATED')
    logger.main('scheduler', 'SCHEDULER TERMINATED')

def wait(wait_time):
    while True:
        now = time.perf_counter()
        if now >= wait_time:
            return
        time.sleep(min(0.001, wait_time - now))

def leniency_timer(timeout, check_flag):
    start = time.perf_counter()
    while time.perf_counter() - start < timeout:
        if check_flag():
            break
        time.sleep(0.005)

# main
def main():
    cycle_time = 5
    cycle_count = 0
    while not SCHEDULER_HALT.is_set():
        cycle_count += 1
        cycle_start = time.perf_counter()
        message = f"STARTING CYCLE {cycle_count}"
        logger.main('scheduler', message)
        # t = 0, start controllers
        signals.vc_start.set()
        signals.ac_start.set()
        # t = 1, stop vc
        wait(cycle_start + schedules.frames_recording_stop)
        # t = ~1, wait on frames in cpm
        signals.frames_arrive.set()
        leniency_timer(leniencies.frames_leniency, lambda: CPM.flags.frames_arrived)
        signals.frames_arrive.clear()
        # t = ~1, frames data set, sending to vai -> t = 3, waiting on vai return
        signals.vai_return.set()
        leniency_timer(leniencies.vai_leniency, lambda: CPM.flags.VAI_arrived)
        signals.vai_return.clear()
        wait(cycle_start + schedules.audio_recording_stop)
        # t = 4, waiting on audio in cpm, sending to aai
        signals.audio_arrive.set()
        leniency_timer(leniencies.audio_leniency, lambda: CPM.flags.audio_arrived)
        signals.audio_arrive.clear()
        # t = 5, waiting on aai return
        signals.aai_return.set()
        leniency_timer(leniencies.aai_leniency, lambda: CPM.flags.AAI_arrived)
        signals.aai_return.clear()
        # t = ~5, waiting out the clock
        remaining = (cycle_start + cycle_time) - time.perf_counter()
        if remaining > 0:
            time.sleep(remaining)
        message = f"CYCLE {cycle_count} ENDED"
        logger.main('scheduler', message)