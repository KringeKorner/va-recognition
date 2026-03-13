from funasr import AutoModel
from pathlib import Path
import json
import numpy as np
import time

# SER models
# emotion2vec_base	(Base emotion representation model)
# emotion2vec_base_finetuned	(Fine‑tuned for 9‑class emotion recognition)
# emotion2vec_plus_seed	(Plus series — pre‑trained SER model)
# emotion2vec_plus_base	(Larger plus series, more data and performance)
# emotion2vec_plus_large (Largest & highest performance)

# parameters
# granularity:
# utterance (1 result for the entire audio file)
# frame (can choose to split it into pieces and provide an analysis for each)
# extract_embedding:
# False (only returns labels + scores)
# True (includes embeddings + scores, which are larger and heavier)

# output_dir	Directory where intermediate outputs are saved (e.g., embeddings saved as .npy).
# batch_size_s	For longer audio or lists, controls processing by seconds (used for batching).
# device	Specify device like "cpu" or "cuda:0" for GPU acceleration (common in other models).
# cache / is_final / chunk_size	Used mainly in streaming ASR/VAD contexts (not typical for batch SER).
# ban_emo_unk	Some SER integrations may offer ways to filter output classes (e.g., ignore "unknown")

SER = AutoModel(
    model = "emotion2vec_plus_large",
    disable_update = True
)

root_path = Path(__file__).resolve().parent
recordings_path = Path(root_path).parent.parent / 'databases' / 'recording_tests'
recording_path = Path(recordings_path) / 'sample_2.wav'
json_path = Path(root_path) / 'output.json'

EMOTION_ORDER = [
    "angry",
    "disgust",
    "fear",
    "happy",
    "sad",
    "surprise",
    "neutral"
]
LABEL_MAP = {
    "angry": "angry",
    "disgusted": "disgust",
    "fearful": "fear",
    "happy": "happy",
    "neutral": "neutral",
    "sad": "sad",
    "surprised": "surprise",
    "other": "other"
}
EMOTIONS = []

def normalize_aai(labels, scores):
    mapped = {}
    for lbl, score in zip(labels, scores):
        new_lbl = LABEL_MAP[lbl]
        if new_lbl == "other":
            continue
        mapped[new_lbl] = score
    ordered_scores = [mapped[e] for e in EMOTION_ORDER]
    return EMOTION_ORDER, ordered_scores

def average(emotion_spread):
    labels = emotion_spread[0][0]
    scores_array = np.array([s[1] for s in emotion_spread])
    avg_scores = np.mean(scores_array, axis=0)
    max_index = np.argmax(avg_scores)
    RESULT = {
        'EMOTION' : labels[max_index],
        'AVG_CONF' : round(float(avg_scores[max_index]), 3),
        'LABELS' : labels
    }
    return RESULT

for recording_path in recordings_path.glob('*.wav'):
    
    print('\nStarting audio analysis')
    time_start = time.perf_counter()

    result = SER.generate(
        str(recording_path),
        granularity="utterance",
        extract_embedding=False
    )

# with open(str(json_path), 'w', encoding='utf-8') as f:
#     json.dump(result, f, ensure_ascii=False, indent=4)

    labels = [lbl.split('/')[-1] for lbl in result[0]['labels']]
    labels.pop()
    scores = [round(score, 3) for score in result[0]['scores']]
    scores.pop()
    labels, scores = normalize_aai(labels, scores)
    EMOTIONS.append([labels, scores])
    result = average(EMOTIONS)
    EMOTIONS.clear()
    time_end = time.perf_counter()
    duration = time_end - time_start
    print(labels)
    print(scores)
    print(f"Returned {result['EMOTION']} with confidence {result['AVG_CONF']}% in {round(duration, 3)}s")