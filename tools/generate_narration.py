"""Generate resumable CosyVoice takes, then fit them to the supplied cue windows."""

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"


def cues():
    draft = (ROOT / "assets/relaxing-a-turkey-timed-draft.md").read_text()
    rows = re.findall(
        r"^\| (\d\d:\d\d\.\d+)–(\d\d:\d\d\.\d+) \| (.*?) \|$", draft, re.MULTILINE
    )

    def seconds(s):
        m, s = s.split(":")
        return 60 * int(m) + float(s)

    result = [
        {"id": i, "start": seconds(a), "end": seconds(b), "text": t}
        for i, (a, b, t) in enumerate(rows, 1)
    ]
    script = (ROOT / "assets/relaxing-a-turkey-script.txt").read_text()
    assert " ".join(script.split()) == " ".join(x["text"] for x in result), (
        "Timing text differs from script"
    )
    assert len(result) == 20
    return result


def generate(rows, only, seed_offset=0, fast=False):
    sys.path[:0] = [
        str(ROOT / ".runtime/CosyVoice"),
        str(ROOT / ".runtime/CosyVoice/third_party/Matcha-TTS"),
    ]
    import torch
    import torchaudio

    # Read WAV directly: avoids optional TorchCodec and FFmpeg ABI dependencies.
    def load_audio(path, **kwargs):
        data, rate = sf.read(path, dtype="float32", always_2d=True)
        return torch.from_numpy(data.T.copy()), rate

    torchaudio.load = load_audio
    torch.set_num_threads(6)
    from cosyvoice.cli.cosyvoice import AutoModel
    from cosyvoice.utils.common import set_all_random_seed

    model = AutoModel(model_dir=str(ROOT / ".runtime/models/CosyVoice3"), fp16=True)
    # Complete phrase from the supplied clip, with matching transcript.
    prompt = "You are a helpful assistant.<|endofprompt|>You got to relax your chicken, because when the chicken is nervous, you cannot cut through this."
    model.add_zero_shot_spk(prompt, str(ROOT / ".runtime/prompt.wav"), "reference")
    for row in rows:
        target = OUT / "takes" / f"{row['id']:02}.wav"
        if only and row["id"] not in only:
            continue
        if target.exists() and not only:
            continue
        set_all_random_seed(20261118 + row["id"] + seed_offset)
        # Pronunciation spelling and punctuation preserve the spoken words.
        spoken = row["text"].replace("debone", "de-bone")
        if row["id"] == 3:
            spoken = spoken[0].upper() + spoken[1:]
        if row["id"] == 19:
            spoken = spoken.replace("And turn", "Turn", 1)
        if fast:
            synthesis = model.inference_instruct2(
                spoken,
                "You are a helpful assistant. 请用尽可能快地语速说一句话。<|endofprompt|>",
                str(ROOT / ".runtime/prompt.wav"),
                stream=False,
                text_frontend=False,
            )
        else:
            synthesis = model.inference_zero_shot(
                spoken,
                "",
                "",
                zero_shot_spk_id="reference",
                stream=False,
                text_frontend=False,
            )
        chunks = [
            x["tts_speech"].detach().float().cpu().numpy().reshape(-1)
            for x in synthesis
        ]
        data = np.concatenate(chunks)
        if row["id"] == 19:
            # Record a separate pickup for the conjunction dropped in full takes.
            prefix = np.concatenate(
                [
                    x["tts_speech"].detach().float().cpu().numpy().reshape(-1)
                    for x in model.inference_zero_shot(
                        "And.",
                        "",
                        "",
                        zero_shot_spk_id="reference",
                        stream=False,
                        text_frontend=False,
                    )
                ]
            )
            data = np.concatenate(
                [
                    trim_edges(prefix, model.sample_rate),
                    np.zeros(round(0.04 * model.sample_rate), dtype=np.float32),
                    trim_edges(data, model.sample_rate),
                ]
            )
        assert np.isfinite(data).all() and np.max(np.abs(data)) > 0.001
        sf.write(target, data, model.sample_rate, subtype="PCM_24")
        print(
            f"TAKE {row['id']:02}: {len(data) / model.sample_rate:.3f}s for {row['end'] - row['start']:.3f}s",
            flush=True,
        )


def trim_edges(data, rate):
    # Keep 35 ms before/after audible content. Never remove internal pauses.
    frame = max(1, int(rate * 0.01))
    padded = np.pad(data, (0, (-len(data)) % frame))
    rms = np.sqrt(np.mean(padded.reshape(-1, frame) ** 2, axis=1))
    active = np.flatnonzero(rms > max(float(rms.max()) * 0.012, 0.00012))
    assert len(active), "Silent take"
    a = max(0, active[0] * frame - int(0.035 * rate))
    b = min(len(data), (active[-1] + 1) * frame + int(0.035 * rate))
    return data[a:b]


def timestamp(sec):
    ms = round(sec * 1000)
    return (
        f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"
    )


def assemble(rows):
    rate = 48000
    render_dir = ROOT / ".runtime/render"
    render_dir.mkdir(parents=True, exist_ok=True)
    timeline = np.zeros(round(rows[-1]["end"] * rate), dtype=np.float32)
    natural = [np.zeros(round(0.44 * rate), dtype=np.float32)]
    report = []
    for row in rows:
        source = OUT / "takes" / f"{row['id']:02}.wav"
        data, sr = sf.read(source, dtype="float32")
        trimmed = trim_edges(data, sr)
        trim_path = render_dir / f"{row['id']:02}-trimmed.wav"
        sf.write(trim_path, trimmed, sr, subtype="PCM_24")
        duration = len(trimmed) / sr
        window = row["end"] - row["start"]
        # Leave natural timing when a take fits; use pitch-preserving stretching
        # only when it overruns, or is significantly shorter than the window.
        speed = (
            duration / (window - 0.025)
            if duration > window - 0.025
            else max(0.85, duration / (window - 0.025))
        )
        fitted = OUT / "cues" / f"{row['id']:02}.wav"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(trim_path),
                "-af",
                f"rubberband=tempo={speed:.9f}:pitch=1",
                "-ar",
                str(rate),
                "-c:a",
                "pcm_s24le",
                str(fitted),
            ],
            check=True,
        )
        fit, _fit_sr = sf.read(fitted, dtype="float32")
        start, end = round(row["start"] * rate), round(row["end"] * rate)
        assert len(fit) <= end - start, f"Cue {row['id']} overrun"
        fade = min(round(0.004 * rate), len(fit) // 2)
        fit[:fade] *= np.linspace(0, 1, fade)
        fit[-fade:] *= np.linspace(1, 0, fade)
        timeline[start : start + len(fit)] = fit
        sf.write(fitted, fit, rate, subtype="PCM_24")
        resampled = render_dir / f"{row['id']:02}-48k.wav"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(trim_path),
                "-ar",
                str(rate),
                "-c:a",
                "pcm_s24le",
                str(resampled),
            ],
            check=True,
        )
        natural.extend(
            [
                sf.read(resampled, dtype="float32")[0],
                np.zeros(round(0.12 * rate), dtype=np.float32),
            ]
        )
        report.append(
            {
                **row,
                "natural_seconds": round(duration, 4),
                "tempo_multiplier": round(speed, 4),
                "speech_end": round(row["start"] + len(fit) / rate, 4),
            }
        )
    # Consistent global gain preserves the dynamics across cue boundaries.
    gain = 0.89125 / max(float(np.max(np.abs(timeline))), 0.001)
    for row in rows:
        fitted = OUT / "cues" / f"{row['id']:02}.wav"
        data, sr = sf.read(fitted, dtype="float32")
        sf.write(fitted, data * gain, sr, subtype="PCM_24")
    sf.write(
        OUT / "relaxing-a-turkey-timed.wav", timeline * gain, rate, subtype="PCM_24"
    )
    untimed = np.concatenate(natural)
    sf.write(
        OUT / "relaxing-a-turkey-natural.wav",
        untimed * (0.89125 / np.max(np.abs(untimed))),
        rate,
        subtype="PCM_24",
    )
    with (OUT / "timing-report.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(report[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(report)
    (OUT / "cues.json").write_text(json.dumps(report, indent=2))
    (OUT / "relaxing-a-turkey.srt").write_text(
        "\n\n".join(
            f"{r['id']}\n{timestamp(r['start'])} --> {timestamp(r['speech_end'])}\n{r['text']}"
            for r in report
        )
        + "\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--assemble-only", action="store_true")
    parser.add_argument("--only", type=int, nargs="+")
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--fast", action="store_true")
    args = parser.parse_args()
    for directory in [OUT, OUT / "takes", OUT / "cues"]:
        directory.mkdir(parents=True, exist_ok=True)
    rows = cues()
    if not args.assemble_only:
        generate(rows, args.only, args.seed_offset, args.fast)
    if all((OUT / "takes" / f"{r['id']:02}.wav").exists() for r in rows):
        assemble(rows)
