# "Hello Bex" – a custom microWakeWord model for ESPHome

A wake word model for **"Hello Bex"**, trained with [microWakeWord](https://github.com/kahrendt/microWakeWord) and running on an ESP32 (DOIT DevKit V1 + INMP441 microphone) with ESPHome and Home Assistant.

It replaces the stock "Hey Jarvis" model, which often missed the wake word with a Turkish accent. The full story is in the build blog (Turkish): *ESP32 ile Kendi Sesli Asistanımı Yapıyorum – Bölüm 6*.

## Use the model

Copy `model/hello_bex.json` and `model/hello_bex.tflite` next to your ESPHome YAML (here in `models/`):

```yaml
micro_wake_word:
  microphone:
    microphone: mic
  models:
    - model: models/hello_bex.json
      id: hello_bex
```

The model needs about 20 KB of tensor arena on the ESP32 (`tensor_arena_size` is set to 30000).

## Results

MixedNet model, 26,049 parameters, 62 KB after 8-bit quantization. Best weights from step 7,500 of 10,000.

Quantized streaming model on the held-out test set (`model/test_results_roc.txt`):

| Cutoff | False rejection rate | False accepts per hour |
|---|---|---|
| **0.94** (default) | 6 % | 0.75 |
| 0.86 | 4 % | 0.94 |
| 0.78 | 4 % | 1.13 |

On the real device, with the author's own (non-native) voice:

| | "Hey Jarvis" (stock model) | "Hello Bex" (this model) |
|---|---|---|
| Average detection probability | 0.90 – 0.96 | **0.97 – 1.00** |
| Default cutoff | 0.97 | 0.94 |
| Tries needed | 2–3 | **1** |

No recordings of the author's voice were used in training. All positive samples are synthetic (Piper TTS).

## Train it yourself

Tested on macOS (Apple M1 Pro, 16 GB RAM), Python 3.11. Training takes about 20 minutes. The data needs about 30 GB of disk space.

```bash
git clone https://github.com/kahrendt/microWakeWord.git
git clone -b mps-support https://github.com/kahrendt/piper-sample-generator.git
curl -L -o piper-sample-generator/models/en_US-libritts_r-medium.pt \
  https://github.com/rhasspy/piper-sample-generator/releases/download/v2.0.0/en_US-libritts_r-medium.pt

python3.11 -m venv .venv
.venv/bin/pip install torch torchaudio piper-phonemize-cross==1.2.1 webrtcvad-wheels audiomentations
.venv/bin/pip install -e ./microWakeWord
.venv/bin/pip install "pymicro-features>=2" "datasets<4" soundfile librosa tensorboard

# 1. Positive samples. Try a few spellings first and pick the one closest to how you say it.
TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1 .venv/bin/python piper-sample-generator/generate_samples.py "hello bex" \
  --max-samples 1000 --batch-size 50 \
  --model piper-sample-generator/models/en_US-libritts_r-medium.pt \
  --output-dir generated_samples

# 2. Augmentation and negative data (downloads ~7 GB)
.venv/bin/python prepare_data.py

# 3. Train and write model/hello_bex.tflite + model/hello_bex.json
.venv/bin/python train.py
```

`prepare_data.py` and `train.py` follow microWakeWord's `basic_training_notebook.ipynb`, with fixes for problems found in October 2026:

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: webrtcvad` on macOS | Install `webrtcvad-wheels` |
| `UnpicklingError: Weights only load failed` (PyTorch ≥ 2.6) | `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1`, only for the official Piper checkpoint |
| `ImportError: ... please install 'torchcodec'` | `datasets<4` |
| AudioSet `.tar` URL returns 404 | AudioSet is now parquet; read it with `pyarrow` + `soundfile` |
| `MicroFrontend has no attribute 'process_samples'` | Use `pymicro-features>=2` from PyPI, not the macOS fork in the notebook |
| `TensorBoard is not installed` at step 500 | Install `tensorboard` |

`TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` lets PyTorch load pickled checkpoints, which can run code. Only use it for files from a source you trust.

## License

The scripts are released under the Apache License 2.0, like microWakeWord.

The model was trained with third-party datasets that have mixed licenses (AudioSet, Free Music Archive, MIT impulse responses, microWakeWord negative sets). **The trained model is for personal, non-commercial use only.** The datasets are not included in this repository; `prepare_data.py` downloads them from their sources.

## Credits

- [microWakeWord](https://github.com/kahrendt/microWakeWord) by Kevin Ahrendt (Apache 2.0): training framework and negative datasets
- [piper-sample-generator](https://github.com/rhasspy/piper-sample-generator) by Michael Hansen (MIT): synthetic speech samples
- [ESPHome micro_wake_word](https://esphome.io/components/micro_wake_word/): on-device detection
- Device: ImpatientMaker's [ESP32 voice assistant](https://github.com/impatientmaker/esphome-voice-assist) (MIT), case remixed from JakeB's "Voice Assist Puck" (CC BY-NC 4.0)
