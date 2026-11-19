"""Light impulse repair and selectable presence EQ for the accepted voice takes."""

import hashlib
import json
import re
import subprocess

import numpy as np
import soundfile as sf
from generate_narration import ROOT
from scipy.signal import correlate, resample_poly, welch

OUT = ROOT / "output"
WORK = ROOT / ".runtime/mastering-v4"
DECLICK = "adeclick=w=30:o=75:a=2:t=5:b=1"
EQ = {
    "balanced": "equalizer=f=350:t=q:w=0.7:g=-1,equalizer=f=2200:t=q:w=0.7:g=2.5,treble=f=3000:t=q:w=0.707:g=3",
    "brighter": "equalizer=f=350:t=q:w=0.7:g=-1,equalizer=f=2200:t=q:w=0.7:g=3.5,treble=f=3000:t=q:w=0.707:g=5",
}
JOBS = [
    ("cosyvoice-cleaned-clip-test", "cosyvoice-polished-test", "balanced"),
    ("cosyvoice-cleaned-clip-test", "cosyvoice-brighter-test", "brighter"),
    (
        "relaxing-a-turkey-from-cleaned-clip-natural",
        "relaxing-a-turkey-polished-natural",
        "balanced",
    ),
    (
        "relaxing-a-turkey-from-cleaned-clip",
        "relaxing-a-turkey-polished-timed",
        "balanced",
    ),
]


def ffmpeg(*args):
    return subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", *map(str, args)],
        capture_output=True,
        text=True,
        check=True,
    )


def band_balance(data, rate):
    frequency, power = welch(data, fs=rate, nperseg=4096)
    mid = power[(frequency >= 200) & (frequency < 1000)].sum()
    upper = power[(frequency >= 2500) & (frequency < 4000)].sum()
    return float(10 * np.log10(upper / mid))


def process(source_name, target_name, preset):
    source = OUT / f"{source_name}.wav"
    original, source_rate = sf.read(source, dtype="float32")
    # Work in float throughout, including the EQ stage where peaks can increase.
    processed = WORK / f"{target_name}-eq.wav"
    filters = f"{DECLICK},{EQ[preset]}"
    restoration = ffmpeg(
        "-i", source, "-af", filters, "-ar", 48000, "-c:a", "pcm_f32le", processed
    )
    click_summary = re.search(
        r"Detected clicks in (\d+) of (\d+) samples", restoration.stderr
    )
    analysis = ffmpeg(
        "-i",
        processed,
        "-af",
        "loudnorm=I=-18:TP=-2:LRA=11:print_format=json",
        "-f",
        "null",
        "-",
    )
    measurements = json.loads(analysis.stderr[analysis.stderr.rfind("{") :])
    normalization = (
        "loudnorm=I=-18:TP=-2:LRA=11:linear=true:print_format=json:"
        f"measured_I={measurements['input_i']}:measured_TP={measurements['input_tp']}:"
        f"measured_LRA={measurements['input_lra']}:measured_thresh={measurements['input_thresh']}:"
        f"offset={measurements['target_offset']}"
    )
    wav = OUT / f"{target_name}.wav"
    final = ffmpeg(
        "-i", processed, "-af", normalization, "-ar", 48000, "-c:a", "pcm_s24le", wav
    )
    final_stats = json.loads(final.stderr[final.stderr.rfind("{") :])
    ffmpeg("-i", wav, "-c:a", "libmp3lame", "-b:a", "192k", OUT / f"{target_name}.mp3")
    audio, rate = sf.read(wav, dtype="float32")
    expected_length = round(len(original) / source_rate * rate)
    assert len(audio) == expected_length and rate == 48000
    assert np.isfinite(audio).all() and np.max(np.abs(audio)) < 0.81
    assert float(final_stats["output_tp"]) <= -1.9
    assert abs(float(final_stats["output_i"]) + 18) < 0.6
    # Check timing against the source over a voiced section, independently of EQ.
    original_48k = resample_poly(original, rate // source_rate, 1)
    x = original_48k[rate : 4 * rate : 4]
    y = audio[rate : 4 * rate : 4]
    lag = int(correlate(y, x, method="fft").argmax()) - len(x) + 1
    shift = lag * 4 / rate
    assert abs(shift) < 0.003, f"Unexpected processing delay: {shift}"
    record = {
        "source": source.name,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output": wav.name,
        "output_sha256": hashlib.sha256(wav.read_bytes()).hexdigest(),
        "preset": preset,
        "filters": filters,
        "normalization": normalization,
        "normalization_result": final_stats,
        "duration_seconds": len(audio) / rate,
        "processing_shift_seconds": shift,
        "sample_peak_dbfs": float(20 * np.log10(np.max(np.abs(audio)))),
        "detected_impulse_samples": int(click_summary[1]) if click_summary else None,
        "input_samples_checked": int(click_summary[2]) if click_summary else None,
        "upper_mid_relative_to_low_mid_change_db": band_balance(audio, rate)
        - band_balance(original, source_rate),
    }
    print(json.dumps(record), flush=True)
    return record


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    records = [process(*job) for job in JOBS]
    (OUT / "polishing-report.json").write_text(json.dumps(records, indent=2) + "\n")
