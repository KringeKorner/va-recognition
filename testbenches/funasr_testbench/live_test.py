from funasr import AutoModel
import sounddevice as sd
import time

SER = AutoModel(
    model = "emotion2vec_plus_large",
    disable_update = True
)

fs = 16000
duration = 3

print('Starting recording')
recording = sd.rec(int(duration*fs), samplerate=fs, channels=2)
sd.wait()
print('Recording terminated, playing back file')
time.sleep(1)
sd.play(recording, fs)
time.sleep(1)
print('Sending for analysis')

result = SER.generate(
        recording,
        granularity="utterance",
        extract_embedding=False,
        fs = 44100
    )

labels = [lbl.split('/')[-1] for lbl in result[0]['labels']]
labels.pop()
scores = [round(score, 3) for score in result[0]['scores']]
scores.pop()
confidence = max(scores)
emotion = labels[scores.index(confidence)]
print(f'Selected {emotion} with confidence {confidence}%')