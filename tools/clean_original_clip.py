"""Restore the supplied WAV before using it as a speech synthesis reference."""

import hashlib
import json
import urllib.request

import numpy as np
import soundfile as sf
from generate_narration import ROOT

MODEL_REVISION = "3eee541a283fd3b8f81b85b1748e3b9ccbefa04d"
MODEL_SHA256 = "70bb6685eb0c2a1d18e2918dca3fbfbd39317010b1802eb1b6ea73a92f3fdec0"
MODEL_URL = (
    f"https://raw.githubusercontent.com/GregorR/rnnoise-models/{MODEL_REVISION}/"
    "somnolent-hogwash-2018-09-01/sh.rnnn"
)
PROMPT_TEXT = (
    "You are a helpful assistant.<|endofprompt|>You use only three finger. "
    "You go up and down, up and down, circular motion."
)


def prepare(work, out, ffmpeg):
    source = ROOT / "assets/my_clip.wav"
    model = work / "speech-denoiser.rnnn"
    if not model.exists():
        urllib.request.urlretrieve(MODEL_URL, model)
    assert hashlib.sha256(model.read_bytes()).hexdigest() == MODEL_SHA256
    original, original_rate = sf.read(source, dtype="float32", always_2d=True)
    assert original_rate == 8000
    duration = len(original) / original_rate
    # Repair impulses before increasing gain. All intermediate WAVs are float.
    repaired = work / "reference-repaired.wav"
    repair_filter = "highpass=f=65,adeclick=t=6:b=1.5"
    ffmpeg(
        "-i",
        source,
        "-ac",
        1,
        "-ar",
        48000,
        "-af",
        repair_filter,
        "-c:a",
        "pcm_f32le",
        repaired,
    )
    data, rate = sf.read(repaired, dtype="float32")
    data *= 0.7 / float(np.max(np.abs(data)))
    sf.write(repaired, data, rate, subtype="FLOAT")
    denoised = work / "reference-denoised.wav"
    denoise_filter = f"arnndn=m={model}:mix=0.75,lowpass=f=3700"
    ffmpeg("-i", repaired, "-af", denoise_filter, "-c:a", "pcm_f32le", denoised)
    cleaned, rate = sf.read(denoised, dtype="float32")
    # This arnndn model has one 10 ms frame of processing delay.
    cleaned = cleaned[round(0.01 * rate) :]
    length = round(duration * rate)
    cleaned = np.pad(cleaned, (0, max(0, length - len(cleaned))))[:length]
    target_rms = 10 ** (-22 / 20)
    gain = min(
        target_rms / np.sqrt(np.mean(cleaned**2)),
        10 ** (-3 / 20) / float(np.max(np.abs(cleaned))),
    )
    cleaned *= gain
    assert np.isfinite(cleaned).all() and float(np.max(np.abs(cleaned))) < 0.71
    full = out / "my_clip-cleaned.wav"
    sf.write(full, cleaned, rate, subtype="PCM_24")
    ffmpeg(
        "-i", full, "-c:a", "libmp3lame", "-b:a", "192k", out / "my_clip-cleaned.mp3"
    )
    prompt = out / "my_clip-cleaned-prompt.wav"
    ffmpeg(
        "-i", full, "-ss", 6.55, "-t", 5.55, "-ar", 24000, "-c:a", "pcm_s24le", prompt
    )
    # Keep an identical copy at the path used by CosyVoice.
    (work / "prompt.wav").write_bytes(prompt.read_bytes())
    record = {
        "reference_source": "assets/my_clip.wav only; no source-video audio",
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "input_rate": original_rate,
        "input_duration": duration,
        "cleaned_reference": str(full.relative_to(ROOT)),
        "cleaned_reference_sha256": hashlib.sha256(full.read_bytes()).hexdigest(),
        "repair_filter": repair_filter,
        "denoise_filter": denoise_filter.replace(str(model), "speech-denoiser.rnnn"),
        "denoiser_model_url": MODEL_URL,
        "denoiser_model_sha256": MODEL_SHA256,
        "denoiser_mix": 0.75,
        "processing_delay_compensated_seconds": 0.01,
        "prompt_start_seconds": 6.55,
        "prompt_duration_seconds": 5.55,
        "prompt_transcript": PROMPT_TEXT,
        "prompt_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
    }
    (out / "original-clip-restoration.json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    return record
