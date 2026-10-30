"""Train the "hello bex" microWakeWord model and write the ESPHome model files.

Follows microWakeWord/notebooks/basic_training_notebook.ipynb (cells 9-11).
Run prepare_data.py first.

Output:
  trained_models/hello_bex/            training checkpoints and logs
  model/hello_bex.tflite               quantized streaming model for the ESP32
  model/hello_bex.json                 ESPHome micro_wake_word model manifest
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

TRAIN_DIR = "trained_models/hello_bex"

config = {
    "window_step_ms": 10,
    "train_dir": TRAIN_DIR,
    "features": [
        {"features_dir": "generated_augmented_features", "sampling_weight": 2.0, "penalty_weight": 1.0, "truth": True, "truncation_strategy": "truncate_start", "type": "mmap"},
        {"features_dir": "negative_datasets/speech", "sampling_weight": 10.0, "penalty_weight": 1.0, "truth": False, "truncation_strategy": "random", "type": "mmap"},
        {"features_dir": "negative_datasets/dinner_party", "sampling_weight": 10.0, "penalty_weight": 1.0, "truth": False, "truncation_strategy": "random", "type": "mmap"},
        {"features_dir": "negative_datasets/no_speech", "sampling_weight": 5.0, "penalty_weight": 1.0, "truth": False, "truncation_strategy": "random", "type": "mmap"},
        # Only used for validation and testing
        {"features_dir": "negative_datasets/dinner_party_eval", "sampling_weight": 0.0, "penalty_weight": 1.0, "truth": False, "truncation_strategy": "split", "type": "mmap"},
    ],
    "training_steps": [10000],
    "positive_class_weight": [1],
    "negative_class_weight": [20],
    "learning_rates": [0.001],
    "batch_size": 128,
    "time_mask_max_size": [0],
    "time_mask_count": [0],
    "freq_mask_max_size": [0],
    "freq_mask_count": [0],
    "eval_step_interval": 500,
    "clip_duration_ms": 1500,
    "target_minimization": 0.9,
    "minimization_metric": None,
    "maximization_metric": "average_viable_recall",
}

with open("training_parameters.yaml", "w") as f:
    yaml.dump(config, f)

subprocess.run(
    [
        sys.executable, "-m", "microwakeword.model_train_eval",
        "--training_config=training_parameters.yaml",
        "--train", "1",
        "--restore_checkpoint", "1",
        "--test_tf_nonstreaming", "0",
        "--test_tflite_nonstreaming", "0",
        "--test_tflite_nonstreaming_quantized", "0",
        "--test_tflite_streaming", "0",
        "--test_tflite_streaming_quantized", "1",
        "--use_weights", "best_weights",
        "mixednet",
        "--pointwise_filters", "64,64,64,64",
        "--repeat_in_block", "1, 1, 1, 1",
        "--mixconv_kernel_sizes", "[5], [7,11], [9,15], [23]",
        "--residual_connection", "0,0,0,0",
        "--first_conv_filters", "32",
        "--first_conv_kernel_size", "5",
        "--stride", "3",
    ],
    check=True,
)

# ESPHome model manifest, in the format of
# https://github.com/esphome/micro-wake-word-models/tree/main/models/v2
Path("model").mkdir(exist_ok=True)
shutil.copy(f"{TRAIN_DIR}/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite", "model/hello_bex.tflite")
manifest = {
    "type": "micro",
    "wake_word": "Hello Bex",
    "author": "Baran Can Aydın",
    "website": "https://github.com/justicemilitia/bisonar-ai/tree/main/hello-bex-wake-word",
    "model": "hello_bex.tflite",
    "trained_languages": ["en"],
    "version": 2,
    "micro": {
        "probability_cutoff": 0.94,
        "feature_step_size": 10,
        "sliding_window_size": 5,
        "tensor_arena_size": 30000,
        "minimum_esphome_version": "2024.7.0",
    },
}
with open("model/hello_bex.json", "w") as f:
    json.dump(manifest, f, indent=2)

print("Model written to model/hello_bex.tflite and model/hello_bex.json")
