"""Apply one light, parallel texture-smoothing pass to the accepted natural mix."""

import csv
import hashlib
import json
import subprocess

import numpy as np
import soundfile as sf
from generate_narration import ROOT
from scipy.signal import correlate, welch

OUT = ROOT / "output"
WORK = ROOT / ".runtime/smoothing-v7"
FILTER = "anlmdn=s=1:p=0.002:r=0.012:m=8"
WET = 0.75
STEM = "relaxing-a-turkey-natural-smooth"


def ffmpeg(*args):
    return subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", *map(str, args)],
        capture_output=True,
        text=True,
        check=True,
    )


def band_power(audio, rate, low, high):
    frequency, power = welch(audio, fs=rate, nperseg=4096)
    return float(power[(frequency >= low) & (frequency < high)].sum())


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    source = OUT / "relaxing-a-turkey-natural-gentle.wav"
    before, rate = sf.read(source, dtype="float32")
    assert rate == 48000 and len(before) == round(143.15 * rate)
    wet_path = WORK / "nonlocal-means.wav"
    ffmpeg("-i", source, "-af", FILTER, "-c:a", "pcm_f32le", wet_path)
    wet, wet_rate = sf.read(wet_path, dtype="float32")
    assert wet_rate == rate and len(wet) == len(before)
    # This filter flushes its analysis buffer and preserves sample alignment.
    for start in [1, 56, 101]:
        a = before[start * rate : (start + 3) * rate : 4]
        b = wet[start * rate : (start + 3) * rate : 4]
        lag = int(correlate(b, a, method="fft").argmax()) - len(a) + 1
        assert abs(lag) * 4 / rate < 0.001, "Unexpected smoothing delay"
    smooth = (1 - WET) * before + WET * wet
    # Never increase loudness or peak level to make the treatment appear stronger.
    gain = min(1.0, float(abs(before).max() / abs(smooth).max()))
    smooth *= gain
    assert np.isfinite(smooth).all() and abs(smooth).max() < 0.6
    rms_before = float(np.sqrt(np.mean(before**2)))
    rms_after = float(np.sqrt(np.mean(smooth**2)))
    rms_change = 20 * np.log10(rms_after / rms_before)
    assert abs(rms_change) < 0.3, "Smoothing changed the overall level excessively"
    changes = {}
    for label, low, high in [
        ("body", 200, 1000),
        ("presence", 2500, 4000),
        ("air", 4000, 8000),
    ]:
        changes[label] = 10 * np.log10(
            band_power(smooth, rate, low, high) / band_power(before, rate, low, high)
        )
    assert changes["body"] > -0.3 and changes["presence"] > -2 and changes["air"] > -2
    master = OUT / f"{STEM}.wav"
    sf.write(master, smooth, rate, subtype="PCM_24")
    ffmpeg("-i", master, "-c:a", "libmp3lame", "-b:a", "192k", OUT / f"{STEM}.mp3")
    cue = list(csv.DictReader((OUT / "natural-pace-cue-map.csv").open()))[8]
    start, end = (
        round(float(cue["natural_start"]) * rate),
        round(float(cue["natural_end"]) * rate),
    )
    sample = OUT / "cosyvoice-my_clip2-smooth-test.wav"
    sf.write(sample, smooth[start:end], rate, subtype="PCM_24")
    ffmpeg(
        "-i",
        sample,
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        OUT / "cosyvoice-my_clip2-smooth-test.mp3",
    )
    # Same excerpt at essentially identical level: before, 750 ms silence, after.
    comparison = np.concatenate(
        [before[start:end], np.zeros(round(0.75 * rate)), smooth[start:end]]
    )
    compare_path = WORK / "before-after.wav"
    sf.write(compare_path, comparison, rate, subtype="PCM_24")
    ffmpeg(
        "-i",
        compare_path,
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        OUT / "cosyvoice-smoothing-before-after.mp3",
    )
    captions = OUT / "relaxing-a-turkey-natural-gentle.srt"
    (OUT / f"{STEM}.srt").write_bytes(captions.read_bytes())
    record = {
        "source": source.name,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output": master.name,
        "output_sha256": hashlib.sha256(master.read_bytes()).hexdigest(),
        "filter": FILTER,
        "wet_mix": WET,
        "dry_mix": 1 - WET,
        "additional_gain": gain,
        "duration_seconds": len(smooth) / rate,
        "sample_rate": rate,
        "tempo_changed": False,
        "rms_change_db": rms_change,
        "band_power_change_db": changes,
        "source_sample_peak_dbfs": float(20 * np.log10(abs(before).max())),
        "output_sample_peak_dbfs": float(20 * np.log10(abs(smooth).max())),
        "comparison": {
            "file": "cosyvoice-smoothing-before-after.mp3",
            "order": ["before", "after"],
            "excerpt_start": start / rate,
            "excerpt_end": end / rate,
            "gap_seconds": 0.75,
        },
        "video_timing_map": "natural-pace-cue-map.csv",
    }
    (OUT / "smoothing-report.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2), flush=True)


if __name__ == "__main__":
    main()
