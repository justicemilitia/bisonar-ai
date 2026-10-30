"""Prepare training data for the "hello bex" wake word.

Follows microWakeWord/notebooks/basic_training_notebook.ipynb (cells 4, 5, 7, 8),
as a plain script so it can run on the Mac without Jupyter.

Steps (each is skipped if its output folder already exists):
  1. Room impulse responses (MIT RIR)        -> mit_rirs/
  2. Background noise (one AudioSet part)    -> audioset_16k/
  3. Background music (FMA extra small)      -> fma_16k/
  4. Augmented positive features             -> generated_augmented_features/
  5. Negative features (speech, noise, ...)  -> negative_datasets/

The downloaded data has mixed licenses: the trained model is for personal,
non-commercial use only.
"""

import os

import urllib.request
import zipfile
from pathlib import Path

import datasets
import numpy as np
import scipy.io.wavfile
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)


def download(url: str, dest: Path) -> None:
    if dest.exists():
        return
    print(f"Downloading {url}", flush=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(dest)


def save_16k_wavs(files: list[str], output_dir: Path, suffix: str) -> None:
    output_dir.mkdir()
    ds = datasets.Dataset.from_dict({"audio": files})
    ds = ds.cast_column("audio", datasets.Audio(sampling_rate=16000))
    for row in tqdm(ds, desc=output_dir.name):
        name = Path(row["audio"]["path"]).name.replace(suffix, ".wav")
        scipy.io.wavfile.write(output_dir / name, 16000, (row["audio"]["array"] * 32767).astype(np.int16))


# 1. Room impulse responses
if not Path("mit_rirs").exists():
    Path("mit_rirs").mkdir()
    rir = datasets.load_dataset("davidscripka/MIT_environmental_impulse_responses", split="train", streaming=True)
    for row in tqdm(rir, desc="mit_rirs"):
        name = row["audio"]["path"].split("/")[-1]
        scipy.io.wavfile.write(Path("mit_rirs") / name, 16000, (row["audio"]["array"] * 32767).astype(np.int16))

# 2. Background noise: one part of AudioSet.
# The dataset moved from .tar archives (as in the notebook) to parquet files.
if not Path("audioset_16k").exists():
    Path("audioset").mkdir(exist_ok=True)
    parquet_path = Path("audioset/bal_train_09.parquet")
    download("https://huggingface.co/datasets/agkphysics/AudioSet/resolve/main/data/bal_train/09.parquet", parquet_path)
    # Read with pyarrow: the parquet schema metadata is from datasets 4, which datasets 3 cannot parse.
    import io

    import librosa
    import pyarrow.parquet as pq
    import soundfile

    Path("audioset_16k").mkdir()
    audio = pq.read_table(parquet_path, columns=["audio"]).column("audio").to_pylist()
    for row in tqdm(audio, desc="audioset_16k"):
        data, rate = soundfile.read(io.BytesIO(row["bytes"]), dtype="float32", always_2d=True)
        data = librosa.resample(data.mean(axis=1), orig_sr=rate, target_sr=16000)
        name = Path(row["path"]).name.replace(".flac", ".wav")
        scipy.io.wavfile.write(Path("audioset_16k") / name, 16000, (np.clip(data, -1, 1) * 32767).astype(np.int16))
    parquet_path.unlink()

# 3. Background music: Free Music Archive (extra small)
if not Path("fma_16k").exists():
    Path("fma").mkdir(exist_ok=True)
    zip_path = Path("fma/fma_xs.zip")
    download("https://huggingface.co/datasets/mchl914/fma_xsmall/resolve/main/fma_xs.zip", zip_path)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall("fma")
    save_16k_wavs([str(p) for p in Path("fma/fma_small").glob("**/*.mp3")], Path("fma_16k"), ".mp3")

# 4. Augment the "hello bex" samples and turn them into spectrogram features
if not Path("generated_augmented_features").exists():
    from mmap_ninja.ragged import RaggedMmap

    from microwakeword.audio.augmentation import Augmentation
    from microwakeword.audio.clips import Clips
    from microwakeword.audio.spectrograms import SpectrogramGeneration

    clips = Clips(
        input_directory="generated_samples",
        file_pattern="*.wav",
        max_clip_duration_s=None,
        remove_silence=False,
        random_split_seed=10,
        split_count=0.1,
    )
    augmenter = Augmentation(
        augmentation_duration_s=3.2,
        augmentation_probabilities={
            "SevenBandParametricEQ": 0.1,
            "TanhDistortion": 0.1,
            "PitchShift": 0.1,
            "BandStopFilter": 0.1,
            "AddColorNoise": 0.1,
            "AddBackgroundNoise": 0.75,
            "Gain": 1.0,
            "RIR": 0.5,
        },
        impulse_paths=["mit_rirs"],
        background_paths=["fma_16k", "audioset_16k"],
        background_min_snr_db=-5,
        background_max_snr_db=10,
        min_jitter_s=0.195,
        max_jitter_s=0.205,
    )

    for split, split_name, repetition, slide_frames in [
        ("training", "train", 2, 10),
        ("validation", "validation", 1, 10),
        ("testing", "test", 1, 1),
    ]:
        out_dir = Path("generated_augmented_features") / split
        out_dir.mkdir(parents=True)
        spectrograms = SpectrogramGeneration(clips=clips, augmenter=augmenter, slide_frames=slide_frames, step_ms=10)
        RaggedMmap.from_generator(
            out_dir=str(out_dir / "wakeword_mmap"),
            sample_generator=spectrograms.spectrogram_generator(split=split_name, repeat=repetition),
            batch_size=100,
            verbose=True,
        )

# 5. Negative features, already computed by the microWakeWord author
if not Path("negative_datasets").exists():
    Path("negative_datasets").mkdir()
    for fname in ["dinner_party.zip", "dinner_party_eval.zip", "no_speech.zip", "speech.zip"]:
        zip_path = Path("negative_datasets") / fname
        download("https://huggingface.co/datasets/kahrendt/microwakeword/resolve/main/" + fname, zip_path)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall("negative_datasets")
        zip_path.unlink()

print("Data ready", flush=True)
