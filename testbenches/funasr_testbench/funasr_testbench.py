from funasr import AutoModel
from pathlib import Path
import json
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
    confidence = max(scores)
    emotion = labels[scores.index(confidence)]
    time_end = time.perf_counter()
    duration = time_end - time_start
    print(labels)
    print(scores)
    print(f'Selected {emotion} with confidence {confidence}% in {duration:.3f}s')