"""Regenerate from the matching full-bandwidth reference and render a clean mix."""

import argparse
import hashlib
import json
import subprocess
import sys

import numpy as np
import soundfile as sf
from generate_narration import ROOT, cues, timestamp, trim_edges

WORK = ROOT / ".runtime/clean-v2"
OUT = ROOT / "output"
REFERENCE_OFFSET = 39.649125  # 0.99266 normalized correlation with my_clip.wav.
REFERENCE_TEXT = (
    "You are a helpful assistant.<|endofprompt|>You got to relax your chicken, "
    "because when the chicken is nervous, you cannot cut through this."
)
STEM = "relaxing-a-turkey-cleaned"
REPORT_NAME = "cleanup-report.json"
FAST_CUES = {4, 17, 20}
FINISH_FILTERS = "highpass=f=70,adeclick=t=5:b=2,afftdn=nr=4:nf=-55,lowpass=f=7200:p=2"
EXPORT_NATURAL = False
REFERENCE_DETAILS = {
    "reference_source": "Supplied video: same passage as my_clip.wav, original 44.1 kHz AAC",
    "clip_match_correlation": 0.992657840773224,
    "reference_start_seconds": REFERENCE_OFFSET + 0.6,
    "reference_duration_seconds": 4.6,
}


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True)


def prepare_reference():
    video = ROOT / "assets/Martin Yan's China-Relaxing A Chicken [2_EztXjmtPY].mp4"
    ffmpeg(
        "-i",
        video,
        "-ss",
        REFERENCE_OFFSET + 0.6,
        "-t",
        4.6,
        "-vn",
        "-ac",
        1,
        "-ar",
        24000,
        "-af",
        "highpass=f=65",
        "-c:a",
        "pcm_f32le",
        WORK / "prompt.wav",
    )


def generate(rows, only, seed_offset):
    sys.path[:0] = [
        str(ROOT / ".runtime/CosyVoice"),
        str(ROOT / ".runtime/CosyVoice/third_party/Matcha-TTS"),
    ]
    import torch
    import torchaudio

    def load_audio(path, **kwargs):
        data, rate = sf.read(path, dtype="float32", always_2d=True)
        return torch.from_numpy(data.T.copy()), rate

    torchaudio.load = load_audio
    torch.set_num_threads(6)
    from cosyvoice.cli.cosyvoice import AutoModel
    from cosyvoice.utils.common import set_all_random_seed

    model = AutoModel(model_dir=str(ROOT / ".runtime/models/CosyVoice3"), fp16=False)
    # Preserve waveform peaks until final gain adjustment; the default clips at .99.
    model.model.hift.audio_limit = float("inf")
    model.add_zero_shot_spk(REFERENCE_TEXT, str(WORK / "prompt.wav"), "reference")
    for row in rows:
        target = WORK / "takes" / f"{row['id']:02}.wav"
        if only and row["id"] not in only:
            continue
        if target.exists() and not only:
            continue
        seed = 20261118 + row["id"] + seed_offset
        set_all_random_seed(seed)
        text = row["text"].replace("debone", "de-bone")
        text = text[0].upper() + text[1:]
        fast = row["id"] in FAST_CUES
        if fast:
            synthesis = model.inference_instruct2(
                text,
                "You are a helpful assistant. 请用尽可能快地语速说一句话。<|endofprompt|>",
                str(WORK / "prompt.wav"),
                stream=False,
                text_frontend=False,
            )
        else:
            synthesis = model.inference_zero_shot(
                text,
                "",
                "",
                zero_shot_spk_id="reference",
                stream=False,
                text_frontend=False,
            )
        audio = np.concatenate(
            [
                x["tts_speech"].detach().float().cpu().numpy().reshape(-1)
                for x in synthesis
            ]
        )
        assert np.isfinite(audio).all() and np.max(np.abs(audio)) > 0.001
        sf.write(target, audio, model.sample_rate, subtype="FLOAT")
        metadata = {
            "seed": seed,
            "fast_instruction": fast,
            "text": text,
            "unclipped_peak": float(np.max(np.abs(audio))),
        }
        target.with_suffix(".json").write_text(json.dumps(metadata, indent=2))
        print(
            f"TAKE {row['id']:02}: {len(audio) / model.sample_rate:.3f}s peak={metadata['unclipped_peak']:.3f}",
            flush=True,
        )


def render(rows):
    rate = 48000
    timeline = np.zeros(round(rows[-1]["end"] * rate), dtype=np.float32)
    report = []
    natural = [np.zeros(round(0.44 * rate), dtype=np.float32)]
    for row in rows:
        path = WORK / "takes" / f"{row['id']:02}.wav"
        data, sr = sf.read(path, dtype="float32")
        data = trim_edges(data, sr)
        if EXPORT_NATURAL:
            from scipy.signal import resample_poly

            natural.extend(
                [
                    resample_poly(data, 2, 1),
                    np.zeros(round(0.15 * rate), dtype=np.float32),
                ]
            )
        # Float WAV retains values above 1; pre-attenuate before restoration.
        pre_gain = min(1.0, 0.8 / float(np.max(np.abs(data))))
        trimmed = WORK / f"{row['id']:02}-trimmed.wav"
        sf.write(trimmed, data * pre_gain, sr, subtype="FLOAT")
        duration = len(data) / sr
        window = row["end"] - row["start"]
        speed = max(1.0, duration / (window - 0.08))
        fitted = WORK / "cues" / f"{row['id']:02}.wav"
        filters = FINISH_FILTERS
        if speed > 1.0:
            remaining = speed
            while remaining > 2:
                filters += ",atempo=2"
                remaining /= 2
            filters += f",atempo={remaining:.9f}"
        ffmpeg("-i", trimmed, "-af", filters, "-ar", rate, "-c:a", "pcm_f32le", fitted)
        audio, _ = sf.read(fitted, dtype="float32")
        audio /= pre_gain
        assert np.isfinite(audio).all()
        assert np.max(np.abs(audio)) < 2 * np.max(np.abs(data)), (
            "Filter introduced a peak spike"
        )
        start, end = round(row["start"] * rate), round(row["end"] * rate)
        assert len(audio) <= end - start
        fade = min(round(0.012 * rate), len(audio) // 2)
        ramp = np.sin(np.linspace(0, np.pi / 2, fade)) ** 2
        audio[:fade] *= ramp
        audio[-fade:] *= ramp[::-1]
        timeline[start : start + len(audio)] = audio
        sf.write(fitted, audio, rate, subtype="FLOAT")
        metadata = json.loads(path.with_suffix(".json").read_text())
        metadata["synthesis_text"] = metadata.pop("text")
        report.append(
            {
                **row,
                "natural_seconds": duration,
                "tempo_multiplier": speed,
                "speech_end": row["start"] + len(audio) / rate,
                **metadata,
                "filters": filters,
            }
        )
    gain = 10 ** (-2 / 20) / float(np.max(np.abs(timeline)))
    timeline *= gain
    master = OUT / f"{STEM}.wav"
    intermediate = WORK / "before-loudness.wav"
    sf.write(intermediate, timeline, rate, subtype="FLOAT")
    analysis = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(intermediate),
            "-af",
            "loudnorm=I=-18:TP=-2:LRA=7:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    stats = json.loads(analysis.stderr[analysis.stderr.rfind("{") :])
    normalize = (
        "loudnorm=I=-18:TP=-2:LRA=7:linear=false:"
        f"measured_I={stats['input_i']}:measured_TP={stats['input_tp']}:"
        f"measured_LRA={stats['input_lra']}:measured_thresh={stats['input_thresh']}:"
        f"offset={stats['target_offset']}"
    )
    ffmpeg(
        "-i", intermediate, "-af", normalize, "-ar", rate, "-c:a", "pcm_s24le", master
    )
    timeline, actual_rate = sf.read(master, dtype="float32")
    assert actual_rate == rate and len(timeline) == round(rows[-1]["end"] * rate)
    ffmpeg(
        "-i",
        master,
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        OUT / f"{STEM}.mp3",
    )
    (OUT / f"{STEM}.srt").write_text(
        "\n\n".join(
            f"{r['id']}\n{timestamp(r['start'])} --> {timestamp(r['speech_end'])}\n{r['text']}"
            for r in report
        )
        + "\n"
    )
    record = {
        **REFERENCE_DETAILS,
        "inference": "CosyVoice3, fp32, vocoder clamp disabled; float intermediate WAVs",
        "filters": filters,
        "gain": gain,
        "loudness_normalization": normalize,
        "sample_rate": rate,
        "duration": len(timeline) / rate,
        "sample_peak_dbfs": 20 * np.log10(float(np.max(np.abs(timeline)))),
        "sha256": hashlib.sha256(master.read_bytes()).hexdigest(),
        "cues": report,
    }
    (OUT / REPORT_NAME).write_text(json.dumps(record, indent=2) + "\n")
    if EXPORT_NATURAL:
        unfit = np.concatenate(natural)
        unfit *= 10 ** (-2 / 20) / float(np.max(np.abs(unfit)))
        sf.write(OUT / f"{STEM}-natural.wav", unfit, rate, subtype="PCM_24")
        ffmpeg(
            "-i",
            OUT / f"{STEM}-natural.wav",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            OUT / f"{STEM}-natural.mp3",
        )
        # Unstretched, unfiltered generated speech for judging the actual clone.
        test, test_rate = sf.read(WORK / "takes/09.wav", dtype="float32")
        test *= 10 ** (-2 / 20) / float(np.max(np.abs(test)))
        test_path = OUT / "cosyvoice-cleaned-clip-test.wav"
        sf.write(test_path, test, test_rate, subtype="PCM_24")
        ffmpeg(
            "-i",
            test_path,
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            OUT / "cosyvoice-cleaned-clip-test.mp3",
        )
    print(f"RENDERED {master}: {len(timeline) / rate}s", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=int, nargs="+")
    parser.add_argument("--seed-offset", type=int, default=1000)
    parser.add_argument("--render-only", action="store_true")
    parser.add_argument("--clean-original", action="store_true")
    args = parser.parse_args()
    if args.clean_original:
        from clean_original_clip import PROMPT_TEXT

        WORK = ROOT / ".runtime/clean-v3-original"
        REFERENCE_TEXT = PROMPT_TEXT
        STEM = "relaxing-a-turkey-from-cleaned-clip"
        REPORT_NAME = "original-clip-narration-report.json"
        FAST_CUES = set()
        FINISH_FILTERS = "anull"
        EXPORT_NATURAL = True
    for path in [WORK, WORK / "takes", WORK / "cues"]:
        path.mkdir(parents=True, exist_ok=True)
    rows = cues()
    if not args.render_only:
        if args.clean_original:
            from clean_original_clip import prepare

            REFERENCE_DETAILS = prepare(WORK, OUT, ffmpeg)
        else:
            prepare_reference()
        generate(rows, args.only, args.seed_offset)
    elif args.clean_original:
        REFERENCE_DETAILS = json.loads(
            (OUT / "original-clip-restoration.json").read_text()
        )
    if all((WORK / "takes" / f"{r['id']:02}.wav").exists() for r in rows):
        render(rows)
