"""Kitten TTS 2 reference-cloned narration at natural pace, without output effects."""

import argparse
import csv
import hashlib
import importlib.metadata
import json
import subprocess
import time

import numpy as np
import soundfile as sf
from generate_narration import ROOT, timestamp, trim_edges
from scipy.signal import resample_poly

MODEL_ID = "KittenML/kitten-tts-2"
MODEL_REVISION = "c93cb7c271baa51d9ae8204d5277988906f235a2"
CODE_REVISION = "5802f6b956844919ecf210f4e55f4750a6ad7c6f"
MODEL_DIR = ROOT / ".runtime/models/KittenTTS2"
WORK = ROOT / ".runtime/kitten-narration"
OUT = ROOT / "output"
REFERENCE_TEXT = (
    "Somehow my mother never get out of work until probably about six thirty or seven. "
    "So I used to go to the wet market and pick up some vegetables for my mother."
)
REFERENCE_START = 4.85
REFERENCE_END = 12.97325
RATE = 48000
PEAK = 10 ** (-5.5 / 20)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True)


def ensure_model():
    marker = MODEL_DIR / "source-revision.txt"
    if marker.exists() and marker.read_text().strip() == MODEL_REVISION:
        return
    from huggingface_hub import hf_hub_download, snapshot_download
    from kittenml.get_model import _kitten2_files

    with open(
        hf_hub_download(MODEL_ID, "config.json", revision=MODEL_REVISION)
    ) as config_stream:
        config = json.load(config_stream)
    snapshot_download(
        MODEL_ID,
        revision=MODEL_REVISION,
        local_dir=str(MODEL_DIR),
        allow_patterns=_kitten2_files(config, decoder="default", weights="packed"),
        max_workers=4,
    )
    marker.write_text(MODEL_REVISION + "\n")


def reference():
    source = ROOT / "assets/my_clip2.wav"
    fingerprint = {
        "source_sha256": digest(source),
        "script_sha256": digest(ROOT / "assets/relaxing-a-turkey-script.txt"),
        "model_revision": MODEL_REVISION,
        "prompt_start": REFERENCE_START,
        "prompt_end": REFERENCE_END,
        "transcript": REFERENCE_TEXT,
    }
    cache_record = WORK / "input-fingerprint.json"
    if (
        cache_record.exists()
        and any((WORK / "takes").glob("*.wav"))
        and json.loads(cache_record.read_text()) != fingerprint
    ):
        raise ValueError(
            "Inputs changed: preserve or remove cached takes before regenerating"
        )
    cache_record.write_text(json.dumps(fingerprint, indent=2) + "\n")
    path = OUT / "kitten-my_clip2-reference.wav"
    ffmpeg(
        "-i",
        source,
        "-ss",
        REFERENCE_START,
        "-t",
        REFERENCE_END - REFERENCE_START,
        "-ac",
        1,
        "-ar",
        24000,
        "-c:a",
        "pcm_s24le",
        path,
    )
    assert 5 <= sf.info(path).duration <= 30
    (OUT / "kitten-my_clip2-reference.txt").write_text(REFERENCE_TEXT + "\n")
    return path, {
        "source": str(source.relative_to(ROOT)),
        "source_sha256": digest(source),
        "prompt_start": REFERENCE_START,
        "prompt_end": REFERENCE_END,
        "prompt_duration": sf.info(path).duration,
        "prompt_sha256": digest(path),
        "transcript": REFERENCE_TEXT,
        "preparation": "mono conversion and resampling only",
    }


def generate(paragraphs, prompt, only, offset):
    import torch
    from kittenml import KittenTTS

    torch.set_num_threads(6)
    model = KittenTTS(
        str(MODEL_DIR), device="cuda", decoder="default", weights="packed"
    )
    # Generate the comparison passage first, then complete the remaining paragraphs.
    for index in [5] + [i for i in range(1, len(paragraphs) + 1) if i != 5]:
        path = WORK / "takes" / f"{index:02}.wav"
        if only and index not in only:
            continue
        if path.exists() and not only:
            continue
        text = paragraphs[index - 1].replace("—", ". ").replace("debone", "de-bone")
        seed = 20261120 + index + offset
        started = time.monotonic()
        audio = model.generate(
            text,
            reference=str(prompt),
            reference_text=REFERENCE_TEXT,
            preset="stable",
            use_reference_prompt=True,
            max_new_tokens=1000,
            advanced={"seed": seed},
        )
        audio = np.asarray(audio, dtype=np.float32).reshape(-1)
        assert np.isfinite(audio).all() and abs(audio).max() > 0.001
        sf.write(path, audio, model.sample_rate, subtype="FLOAT")
        info = {
            "paragraph": index,
            "text": paragraphs[index - 1],
            "synthesis_text": text,
            "seed": seed,
            "native_rate": model.sample_rate,
            "duration": len(audio) / model.sample_rate,
            "sample_peak": float(abs(audio).max()),
            "samples_at_vocoder_limit": int((abs(audio) >= 0.98999).sum()),
            "elapsed_seconds": time.monotonic() - started,
            "use_reference_prompt": True,
        }
        path.with_suffix(".json").write_text(json.dumps(info, indent=2) + "\n")
        print(json.dumps(info), flush=True)


def assemble(paragraphs, reference_info):
    native = []
    rows = []
    cursor = round(0.44 * RATE)
    for index, text in enumerate(paragraphs, 1):
        path = WORK / "takes" / f"{index:02}.wav"
        audio, sr = sf.read(path, dtype="float32")
        audio = resample_poly(trim_edges(audio, sr), RATE // sr, 1)
        fade = min(round(0.012 * RATE), len(audio) // 2)
        ramp = np.sin(np.linspace(0, np.pi / 2, fade)) ** 2
        audio[:fade] *= ramp
        audio[-fade:] *= ramp[::-1]
        row = {
            "paragraph": index,
            "start": cursor / RATE,
            "end": (cursor + len(audio)) / RATE,
            "text": text,
        }
        rows.append(row)
        native.extend([audio, np.zeros(round(0.15 * RATE), dtype=np.float32)])
        cursor += len(audio) + round(0.15 * RATE)
    combined = np.concatenate([np.zeros(round(0.44 * RATE), dtype=np.float32), *native])
    gain = PEAK / float(abs(combined).max())
    combined *= gain
    master = OUT / "relaxing-a-turkey-kitten-natural.wav"
    sf.write(master, combined, RATE, subtype="PCM_24")
    ffmpeg(
        "-i",
        master,
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        OUT / "relaxing-a-turkey-kitten-natural.mp3",
    )
    sample = rows[4]
    start, end = round(sample["start"] * RATE), round(sample["end"] * RATE)
    test = OUT / "kitten-tts-voice-test.wav"
    sf.write(test, combined[start:end], RATE, subtype="PCM_24")
    ffmpeg(
        "-i",
        test,
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        OUT / "kitten-tts-voice-test.mp3",
    )
    import pyloudnorm as pyln

    cosy_path = OUT / "cosyvoice-my_clip2-balanced-test.wav"
    cosy, cosy_rate = sf.read(cosy_path, dtype="float32")
    assert cosy_rate == RATE
    kitten_sample = combined[start:end]
    meter = pyln.Meter(RATE)
    levels = [meter.integrated_loudness(cosy), meter.integrated_loudness(kitten_sample)]
    target_level = min(levels)
    comparison_gains = [10 ** ((target_level - level) / 20) for level in levels]
    comparison = np.concatenate(
        [
            cosy * comparison_gains[0],
            np.zeros(round(0.75 * RATE), dtype=np.float32),
            kitten_sample * comparison_gains[1],
        ]
    )
    compare_path = WORK / "cosyvoice-vs-kitten.wav"
    sf.write(compare_path, comparison, RATE, subtype="PCM_24")
    ffmpeg(
        "-i",
        compare_path,
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        OUT / "cosyvoice-vs-kitten.mp3",
    )
    with (OUT / "kitten-natural-timing.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (OUT / "relaxing-a-turkey-kitten-natural.srt").write_text(
        "\n\n".join(
            f"{i}\n{timestamp(r['start'])} --> {timestamp(r['end'])}\n{r['text']}"
            for i, r in enumerate(rows, 1)
        )
        + "\n"
    )
    # Major action boundaries use whole script paragraphs; these are planning estimates.
    labels = {
        5: ("Main-course joke", 38.12),
        6: ("Three-finger massage", 46.32),
        8: ("Wing movement", 56.76),
        10: ("Nervous / relaxed lead-in", 66.84),
        11: ("Countdown lead-in", 69.8),
        12: ("First cutting call", 75.48),
        13: ("Breast / tenderloin", 80.28),
        14: ("Turn around / remaining pieces", 87.76),
        15: ("Thanksgiving greeting", 97.2),
    }
    anchors = [
        {
            "action": label,
            "source_seconds": old,
            "kitten_seconds": rows[i - 1]["start"],
            "basis": "Source draft/previous speech anchor to new paragraph boundary; visually review",
        }
        for i, (label, old) in labels.items()
    ]
    with (OUT / "kitten-action-timing.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(anchors[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(anchors)
    report = {
        "engine": "Kitten TTS 2",
        "package": "kittenml",
        "package_version": importlib.metadata.version("kittenml"),
        "code_revision": CODE_REVISION,
        "model": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "weights": "packed (lossless)",
        "decoder": "default",
        "preset": "stable",
        "reference": reference_info,
        "script_sha256": digest(ROOT / "assets/relaxing-a-turkey-script.txt"),
        "native_rate": 24000,
        "export_rate": RATE,
        "duration_seconds": len(combined) / RATE,
        "sample_start": sample["start"],
        "sample_end": sample["end"],
        "sample_duration": (end - start) / RATE,
        "gain": gain,
        "peak_dbfs": float(20 * np.log10(abs(combined).max())),
        "time_stretching": False,
        "output_noise_reduction": False,
        "output_eq": False,
        "comparison": {
            "file": "cosyvoice-vs-kitten.mp3",
            "order": ["CosyVoice balanced mix", "Kitten TTS 2"],
            "cosy_source": cosy_path.name,
            "source_lufs": levels,
            "target_lufs": target_level,
            "static_gains": comparison_gains,
            "gap_seconds": 0.75,
            "note": "Only the louder excerpt is attenuated; no comparison limiting or EQ",
        },
        "paragraphs": [
            json.loads((WORK / "takes" / f"{i:02}.json").read_text())
            for i in range(1, len(paragraphs) + 1)
        ],
        "outputs": {
            p.name: {"sha256": digest(p), "bytes": p.stat().st_size}
            for p in [master, test]
        },
        "environment": {
            p: importlib.metadata.version(p)
            for p in [
                "torch",
                "torchaudio",
                "transformers",
                "diffusers",
                "s3tokenizer",
                "numpy",
                "soundfile",
            ]
        },
    }
    (OUT / "kitten-generation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "RENDERED",
        json.dumps(
            {k: report[k] for k in ["duration_seconds", "sample_duration", "peak_dbfs"]}
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=int, nargs="+")
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--assemble-only", action="store_true")
    args = parser.parse_args()
    for path in [WORK, WORK / "takes", OUT]:
        path.mkdir(parents=True, exist_ok=True)
    paragraphs = (
        (ROOT / "assets/relaxing-a-turkey-script.txt").read_text().strip().split("\n\n")
    )
    assert len(paragraphs) == 15 and paragraphs[4].startswith("He said,")
    prompt, reference_info = reference()
    if not args.assemble_only:
        ensure_model()
        generate(paragraphs, prompt, args.only, args.seed_offset)
    if all(
        (WORK / "takes" / f"{i:02}.wav").exists() for i in range(1, len(paragraphs) + 1)
    ):
        assemble(paragraphs, reference_info)
