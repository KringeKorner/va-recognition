from pathlib import Path
import sounddevice as sd
import time
import wavio

root_path = Path(__file__).resolve().parent
recordings_path = Path(root_path).parent.parent / 'databases' / 'recording_tests'
recording_path = Path(recordings_path) / 'sample_3.wav'

fs = 16000
duration = 5

print('Starting recording')
recording = sd.rec(int(duration*fs), samplerate=fs, channels=2)
sd.wait()
print('Recording terminated, saving')
wavio.write(str(recording_path), recording, fs, sampwidth=4)