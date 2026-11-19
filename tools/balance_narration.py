"""Selective split-band de-essing with a modest body/presence adjustment."""

import csv
import hashlib
import json
import subprocess

import numpy as np
import soundfile as sf
from generate_narration import ROOT
from scipy.signal import correlate, welch

OUT = ROOT / "output"
WORK = ROOT / ".runtime/deessing-v8"
STEM = "relaxing-a-turkey-natural-balanced"
COMPRESSOR = "acompressor=threshold=0.0125:ratio=3:attack=1:release=70:makeup=1:knee=2.828:detection=peak:mix=0.65"
EQ = "bass=f=180:t=q:w=0.707:g=1.5,equalizer=f=2600:t=q:w=0.75:g=1.5"
GRAPH = (
    "[0:a]acrossover=split=4500:order=4th[low][high];"
    "[high]asplit=2[before_high][to_compressor];"
    f"[to_compressor]{COMPRESSOR},asplit=2[after_high][mix_high];"
    f"[low][mix_high]amix=inputs=2:normalize=0,{EQ}[balanced]"
)


def ffmpeg(*args):
    return subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", *map(str, args)],
        capture_output=True,
        text=True,
        check=True,
    )


def band_power(audio, rate, low, high):
    f, p = welch(audio, fs=rate, nperseg=4096)
    return float(p[(f >= low) & (f < high)].sum())


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    source = OUT / "relaxing-a-turkey-natural-smooth.wav"
    original, rate = sf.read(source, dtype="float32")
    assert rate == 48000 and len(original) == round(143.15 * rate)
    raw = WORK / "balanced-float.wav"
    high_before, high_after = WORK / "high-before.wav", WORK / "high-after.wav"
    ffmpeg(
        "-i",
        source,
        "-filter_complex",
        GRAPH,
        "-map",
        "[balanced]",
        "-c:a",
        "pcm_f32le",
        raw,
        "-map",
        "[before_high]",
        "-c:a",
        "pcm_f32le",
        high_before,
        "-map",
        "[after_high]",
        "-c:a",
        "pcm_f32le",
        high_after,
    )
    audio, sr = sf.read(raw, dtype="float32")
    assert sr == rate and len(audio) == len(original) and np.isfinite(audio).all()
    # Match the comparison's overall level without using another peak limiter.
    rms = lambda a: float(np.sqrt(np.mean(a * a)))
    rms_gain = rms(original) / rms(audio)
    peak_gain = float(abs(original).max() / abs(audio).max())
    gain = min(rms_gain, peak_gain)
    audio *= gain
    assert abs(audio).max() < 0.6
    rms_change = 20 * np.log10(rms(audio) / rms(original))
    assert abs(rms_change) < 0.7
    shifts = []
    for start in [1, 56, 101]:
        a, b = (
            original[start * rate : (start + 3) * rate : 4],
            audio[start * rate : (start + 3) * rate : 4],
        )
        lag = int(correlate(b, a, method="fft").argmax()) - len(a) + 1
        shifts.append(lag * 4 / rate)
    assert max(abs(s) for s in shifts) < 0.003
    master = OUT / f"{STEM}.wav"
    sf.write(master, audio, rate, subtype="PCM_24")
    ffmpeg("-i", master, "-c:a", "libmp3lame", "-b:a", "192k", OUT / f"{STEM}.mp3")
    row = list(csv.DictReader((OUT / "natural-pace-cue-map.csv").open()))[8]
    start, end = (
        round(float(row["natural_start"]) * rate),
        round(float(row["natural_end"]) * rate),
    )
    sample = OUT / "cosyvoice-my_clip2-balanced-test.wav"
    sf.write(sample, audio[start:end], rate, subtype="PCM_24")
    ffmpeg(
        "-i",
        sample,
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        OUT / "cosyvoice-my_clip2-balanced-test.mp3",
    )
    comparison = np.concatenate(
        [original[start:end], np.zeros(round(0.75 * rate)), audio[start:end]]
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
        OUT / "cosyvoice-hiss-before-after.mp3",
    )
    (OUT / f"{STEM}.srt").write_bytes(
        (OUT / "relaxing-a-turkey-natural-smooth.srt").read_bytes()
    )
    hi, _ = sf.read(high_before, dtype="float32")
    ho, _ = sf.read(high_after, dtype="float32")
    frame = round(0.01 * rate)
    length = len(hi) // frame * frame
    hi_rms = np.sqrt(np.mean(hi[:length].reshape(-1, frame) ** 2, axis=1))
    ho_rms = np.sqrt(np.mean(ho[:length].reshape(-1, frame) ** 2, axis=1))
    reduction = 20 * np.log10(np.maximum(ho_rms, 1e-12) / np.maximum(hi_rms, 1e-12))
    active = hi_rms > 0.0005
    changed = active & (reduction < -0.5)
    assert changed.sum() > 0, "De-esser did not affect any high-frequency bursts"
    # Compare tonal balance relative to the mid band, independently of level matching.
    mid0 = band_power(original, rate, 300, 1000)
    mid1 = band_power(audio, rate, 300, 1000)
    balance = {}
    for name, low, high in [
        ("body", 80, 220),
        ("presence", 1500, 3500),
        ("air", 4500, 10000),
    ]:
        balance[name] = 10 * np.log10(
            (band_power(audio, rate, low, high) / mid1)
            / (band_power(original, rate, low, high) / mid0)
        )
    report = {
        "source": source.name,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output": master.name,
        "output_sha256": hashlib.sha256(master.read_bytes()).hexdigest(),
        "export_rate": rate,
        "synthesis_rate": sf.info(OUT / "cosyvoice-my_clip2-test.wav").samplerate,
        "duration_seconds": len(audio) / rate,
        "tempo_changed": False,
        "filter_graph": GRAPH,
        "additional_gain": gain,
        "rms_change_db": rms_change,
        "output_peak_dbfs": float(20 * np.log10(abs(audio).max())),
        "alignment_shift_seconds": shifts,
        "relative_band_balance_change_db": balance,
        "deessing": {
            "crossover_hz": 4500,
            "ten_ms_frames_with_more_than_half_db_reduction": int(changed.sum()),
            "total_ten_ms_frames": len(reduction),
            "max_active_frame_reduction_db": float(-reduction[active].min()),
            "median_changed_frame_reduction_db": float(-np.median(reduction[changed])),
        },
        "comparison": {
            "order": ["previous smoothed mix", "de-essed and balanced mix"],
            "gap_seconds": 0.75,
            "excerpt_start": start / rate,
            "excerpt_end": end / rate,
        },
    }
    (OUT / "deessing-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
