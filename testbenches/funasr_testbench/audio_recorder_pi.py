from pathlib import Path
import numpy as np
import sounddevice as sd
import time
import wavio

root_path = Path(__file__).resolve().parent
recordings_path = Path(root_path).resolve() / 'recordings'
recording_path = Path(recordings_path) / 'sample_1.wav'

fs = 48000
duration = 5
deviceSource = 0 # windows

print('Starting recording')
recording = sd.rec(int(duration*fs), samplerate=fs, channels=1, device=deviceSource)
sd.wait()
print('Recording terminated, saving')
gain = 5.0
recording = recording * gain
recording = np.clip(recording, -1.0, 1.0)
wavio.write(str(recording_path), (recording * (2**31-1)).astype(np.int32), fs, sampwidth=4)
