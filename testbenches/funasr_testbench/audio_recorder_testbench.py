from pathlib import Path
import sounddevice as sd
import time
import wavio

root_path = Path(__file__).resolve().parent
recordings_path = Path(root_path).parent.parent / 'databases' / 'recording_tests'
recording_path = Path(recordings_path) / 'sample_4.wav'

print(sd.query_devices())
fs = 16000
duration = 3
deviceSource = 1 # windows

print('Starting recording')
recording = sd.rec(int(duration*fs), samplerate=fs, channels=1, device=deviceSource)
sd.wait()
print('Recording terminated, saving')
wavio.write(str(recording_path), recording, fs, sampwidth=4)