"""Keep the accepted natural pace, soften peaks, and map picture action anchors."""

import csv
import hashlib
import json
import re
import subprocess

import numpy as np
import soundfile as sf
from generate_narration import ROOT, cues, timestamp, trim_edges
from scipy.signal import correlate, resample_poly

OUT = ROOT / "output"
WORK = ROOT / ".runtime/natural-plan"
TAKES = ROOT / ".runtime/my_clip2-generation/takes"
STEM = "relaxing-a-turkey-natural-gentle"
RATE = 48000
FPS = 30
FILTERS = (
    "adeclick=w=30:o=75:a=2:t=5:b=1,"
    "acompressor=threshold=0.25:ratio=1.6:attack=2:release=90:makeup=1:knee=2.8:detection=peak,"
    "volume=0.891250938"
)


def ffmpeg(*args):
    return subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", *map(str, args)],
        capture_output=True,
        text=True,
        check=True,
    )


def write_csv(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def trim_start(raw, trimmed):
    # Current native float takes and trimmed samples are bit-identical.
    # Locate the exact retained slice for ASR offsets without guessing silence duration.
    for index in np.flatnonzero(raw == trimmed[0]):
        if np.array_equal(raw[index : index + len(trimmed)], trimmed):
            return int(index)
    raise ValueError("Could not locate the retained take inside its source")


def audio_and_cues():
    source = OUT / "relaxing-a-turkey-my_clip2-natural.wav"
    original, rate = sf.read(source, dtype="float32")
    assert rate == RATE
    faded = original.copy()
    reconstructed = np.zeros_like(original)
    rows, cursor = [], round(0.44 * RATE)
    for cue in cues():
        raw, sr = sf.read(TAKES / f"{cue['id']:02}.wav", dtype="float32")
        trimmed = trim_edges(raw, sr)
        kept_start = trim_start(raw, trimmed)
        resampled = resample_poly(trimmed, RATE // sr, 1)
        start, end = cursor, cursor + len(resampled)
        reconstructed[start:end] = resampled
        rows.append(
            {
                "cue": cue["id"],
                "source_start": cue["start"],
                "source_end": cue["end"],
                "natural_start": start / RATE,
                "natural_end": end / RATE,
                "source_start_frame_30fps": round(cue["start"] * FPS),
                "source_end_frame_30fps": round(cue["end"] * FPS),
                "natural_start_frame_30fps": round(start / RATE * FPS),
                "natural_end_frame_30fps": round(end / RATE * FPS),
                "suggested_duration_scale": len(resampled)
                / RATE
                / (cue["end"] - cue["start"]),
                "trimmed_lead_seconds": kept_start / sr,
                "text": cue["text"],
            }
        )
        # Preserve samples and 150 ms gaps; taper only within the existing edge margins.
        count = min(round(0.012 * RATE), (end - start) // 2)
        ramp = np.sin(np.linspace(0, np.pi / 2, count)) ** 2
        faded[start : start + count] *= ramp
        faded[end - count : end] *= ramp[::-1]
        cursor = end + round(0.15 * RATE)
    assert cursor == len(original), (
        "Natural take layout no longer matches the accepted mix"
    )
    reconstruction_gain = 10 ** (-2 / 20) / float(np.max(np.abs(reconstructed)))
    assert np.max(np.abs(original - reconstructed * reconstruction_gain)) < 2e-7, (
        "Cached native takes no longer match the accepted natural narration"
    )
    assembled = WORK / "edge-fades.wav"
    sf.write(assembled, faded, RATE, subtype="FLOAT")
    master = OUT / f"{STEM}.wav"
    result = ffmpeg(
        "-i", assembled, "-af", FILTERS, "-ar", RATE, "-c:a", "pcm_s24le", master
    )
    audio, output_rate = sf.read(master, dtype="float32")
    assert (
        output_rate == RATE and len(audio) == len(original) and np.isfinite(audio).all()
    )
    assert np.max(np.abs(audio)) < 0.6
    # This check allows filter group delay but rejects a changed speaking timeline.
    x, y = original[RATE : 4 * RATE : 4], audio[RATE : 4 * RATE : 4]
    shift = (int(correlate(y, x, method="fft").argmax()) - len(x) + 1) * 4 / RATE
    assert abs(shift) < 0.003
    ffmpeg("-i", master, "-c:a", "libmp3lame", "-b:a", "192k", OUT / f"{STEM}.mp3")
    sample_start, sample_end = rows[8]["natural_start"], rows[8]["natural_end"]
    test = OUT / "cosyvoice-my_clip2-gentle-test.wav"
    sf.write(
        test,
        audio[round(sample_start * RATE) : round(sample_end * RATE)],
        RATE,
        subtype="PCM_24",
    )
    ffmpeg(
        "-i",
        test,
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        OUT / "cosyvoice-my_clip2-gentle-test.mp3",
    )
    srt = (
        "\n\n".join(
            f"{r['cue']}\n{timestamp(r['natural_start'])} --> {timestamp(r['natural_end'])}\n{r['text']}"
            for r in rows
        )
        + "\n"
    )
    (OUT / f"{STEM}.srt").write_text(srt)
    write_csv(OUT / "natural-pace-cue-map.csv", rows)
    detected = re.search(r"Detected clicks in (\d+) of (\d+) samples", result.stderr)
    metadata = {
        "source": source.name,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "output": master.name,
        "output_sha256": hashlib.sha256(master.read_bytes()).hexdigest(),
        "filters": FILTERS,
        "edge_fade_seconds": 0.012,
        "duration_seconds": len(audio) / RATE,
        "sample_rate": RATE,
        "processing_shift_seconds": shift,
        "source_sample_peak_dbfs": float(20 * np.log10(abs(original).max())),
        "output_sample_peak_dbfs": float(20 * np.log10(abs(audio).max())),
        "source_full_scale_samples": int((abs(original) >= 0.999).sum()),
        "output_full_scale_samples": int((abs(audio) >= 0.999).sum()),
        "detected_impulse_samples": int(detected[1]) if detected else None,
        "tempo_changed": False,
        "makeup_gain": False,
    }
    (OUT / "natural-gentle-report.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )
    return rows, metadata


def action_anchors(rows):
    alignment = json.loads((WORK / "word-alignment.json").read_text())
    provenance = {
        "model": "faster-whisper medium.en",
        "native_take_sha256": {
            str(cue): hashlib.sha256((TAKES / f"{cue:02}.wav").read_bytes()).hexdigest()
            for cue in [15, 17, 19]
        },
        "source_video_sha256": hashlib.sha256(
            (
                ROOT / "assets/Martin Yan's China-Relaxing A Chicken [2_EztXjmtPY].mp4"
            ).read_bytes()
        ).hexdigest(),
        "source_excerpts_seconds": [[66, 81], [92, 96.8]],
    }
    if "provenance" in alignment:
        assert alignment["provenance"] == provenance, (
            "Recompute word anchors after source/take changes"
        )
    alignment["provenance"] = provenance
    (WORK / "word-alignment.json").write_text(json.dumps(alignment, indent=2) + "\n")
    source = alignment["source_66_to_81"]
    by_id = {r["cue"]: r for r in rows}

    def find(words, token, occurrence=0):
        matches = [w for w in words if w["word"].lower().strip(",.!?") == token]
        return matches[occurrence]

    def natural_word(cue, token, occurrence=0, edge="start"):
        word = find(alignment[f"cue{cue}"], token, occurrence)
        row = by_id[cue]
        return max(
            row["natural_start"],
            row["natural_start"] + word[edge] - row["trimmed_lead_seconds"],
        )

    anchors = []

    def add(label, old, new, evidence):
        anchors.append(
            {
                "action": label,
                "source_seconds": old,
                "natural_seconds": round(new, 4),
                "source_frame_30fps": round(old * FPS),
                "natural_frame_30fps": round(new * FPS),
                "basis": evidence,
            }
        )

    for label, cue in [
        ("Main-course joke", 9),
        ("Three-finger massage", 10),
        ("Wing movement", 12),
        ("Pay attention", 16),
        ("Finished turkey / greeting", 20),
    ]:
        add(
            label,
            by_id[cue]["source_start"],
            by_id[cue]["natural_start"],
            "Draft cue boundary; review action pose visually",
        )
    for label, old_token, new_token in [
        ("Nervous pose", "nervous", "nervous"),
        ("Relaxed pose", "relax", "relaxed"),
    ]:
        add(
            label,
            66 + find(source, old_token)["start"],
            natural_word(15, new_token),
            "ASR word estimate on source and native take; review frame by frame",
        )
    for label, token, occurrence in [
        ("Countdown three", "three", 0),
        ("Countdown two", "two", 0),
        ("Countdown one", "one", 0),
        ("First cutting call", "one", 1),
    ]:
        add(
            label,
            66 + find(source, token, occurrence)["start"],
            natural_word(17, token, occurrence),
            "ASR word estimate on source and native take; review frame by frame",
        )
    add(
        "Last tenderloin line ends",
        92 + find(alignment["source_92_to_96_8"], "that", -1)["end"],
        natural_word(19, "that", -1, edge="end"),
        "ASR end of final 'that' on source and native take; speech anchor, not measured end of physical action",
    )
    anchors.sort(key=lambda a: a["natural_seconds"])
    write_csv(OUT / "natural-pace-action-anchors.csv", anchors)
    (OUT / "natural-pace-word-alignment.json").write_text(
        json.dumps(alignment, indent=2) + "\n"
    )
    return anchors


def editing_plan(rows, metadata, anchors):
    def fmt(seconds):
        return timestamp(seconds)[3:].replace(",", ".")

    chosen = [9, 10, 12, 15, 16, 17, 20]
    labels = {
        9: "Main-course joke",
        10: "Three-finger massage",
        12: "Wing movement",
        15: "Nervous / relaxed poses",
        16: "Pay attention / eighteen seconds",
        17: "Countdown lead-in",
        20: "Finished turkey / Thanksgiving greeting",
    }
    table = "\n".join(
        f"| {r['cue']} | {fmt(r['source_start'])} | {fmt(r['natural_start'])} | {labels[r['cue']]} |"
        for r in rows
        if r["cue"] in chosen
    )
    cutting_start = next(
        a["natural_seconds"] for a in anchors if a["action"] == "First cutting call"
    )
    cutting_end = next(
        a["natural_seconds"]
        for a in anchors
        if a["action"] == "Last tenderloin line ends"
    )
    plan = f"""# Natural narration: audio master and picture timing

The accepted natural narration remains **{metadata["duration_seconds"]:.3f} seconds
(2:23.15)**. The source is 99.614 seconds (1:39.614), a difference of 43.536 seconds,
or about 43.7%. The gentle master retains exactly the same speaking pace, cue
positions and 150 ms gaps. No narration is time-stretched.

## Audio

The previous natural WAV has a sample peak of -2.0 dBFS and no samples at the
digital ceiling. Its MP3 also stays below the digital ceiling. The distortion
described by the user may be in the generated voice, or be a playback/subjective
harshness issue; these measurements do not identify its audible cause.

The new mix adds 12 ms fades inside existing cue-edge margins, a light impulse
repair pass and soft-knee 1.6:1 peak compression with no makeup gain. An additional
1 dB of attenuation leaves a measured sample peak of
{metadata["output_sample_peak_dbfs"]:.2f} dBFS. It does not boost treble, denoise
the voice or run loudness normalization/limiting. This can soften peaks and
clicks but cannot reconstruct speech already distorted during synthesis.

- `relaxing-a-turkey-natural-gentle.wav` / `.mp3`: full 48 kHz mono master.
- `cosyvoice-my_clip2-gentle-test.wav` / `.mp3`: the joke passage extracted from
  the full master at its actual playback volume.
- `relaxing-a-turkey-natural-gentle.srt`: cue captions matching natural timing.
- `natural-gentle-report.json`: processing, hashes and alignment checks.

This mix is intentionally quieter than the preceding natural master. It is a
listening candidate, not a claim that all synthesized distortion is repaired.

## Effect on keyframes

The existing reference images and chosen poses can remain useful. Their new
display times and the lengths of the motion between them must follow the audio.
The following are **dialogue/action reference boundaries**, not detected camera
cuts and not a finished shot list:

| Cue | Original start | Natural start | Dialogue reference |
| --- | --- | --- | --- |
{table}

`natural-pace-cue-map.csv` contains all 20 old/new cue ranges, nominal duration
ratios and nearest-frame positions at the source's 30 fps. Ratios are planning
references: they are not instructions to slow every existing shot by that factor.
`natural-pace-action-anchors.csv` adds word estimates for the nervous/relaxed
poses, countdown and first cutting call. Word timestamps require visual review;
the CSV states whether each source position comes from a draft cue or ASR.

Do not apply one global 43.7% stretch. Individual sections expand differently;
for example, the tense-turkey explanation grows much more than the secret's
location. A pose that belongs on "relaxed" or "one" should land on that word,
not on a uniformly scaled timestamp.

## Picture workflow

1. Approve the natural voice and lock its timeline before generating final motion.
2. Detect actual source cuts separately. Split a dialogue cue wherever a camera
   cut occurs; never interpolate across a cut just because it falls inside a cue.
3. Reuse suitable edited start/end keyframe images as pose references. Change
   the shot durations to the new action anchors. Long sections may need extra
   intermediate pose references or several shorter generated shots.
4. Fill expanded explanatory passages with plausible preparation, reaction,
   ingredient or hand-detail coverage. Avoid simply slowing fast hand movements
   or holding a speaking face unnaturally still for the entire extra duration.
5. Preserve continuous movement through the three-finger massage and wing poses;
   land the nervous/relaxed changes on their estimated word anchors and review
   hand contact and bird anatomy at frame level.
6. Generate/regenerate motion and lip sync against the locked natural audio.
   Adding new audio to an already generated talking face will not synchronize it.
7. Use the natural SRT, then refine subtitles and action joins against the picture.

## The eighteen-second joke

The natural first-cut call is approximately **{fmt(cutting_start)}**; the final
tenderloin commentary ends around **{fmt(cutting_end)}**. That span is about
**{cutting_end - cutting_start:.1f} seconds**, not 18 seconds. These are speech anchors,
not measured physical action durations.

If the video must show a literal uninterrupted eighteen-second deboning, keep
the actual rapid carving insert at 18 seconds and move some explanatory speech
over preparation or finished-piece close-ups before/after it, or revise/shorten
that portion of the script. If the number is simply part of the parody, a longer
sequence can follow the natural narration. Do not stretch the physical carving
uniformly and assume the eighteen-second claim still matches a visible timer.

No video/keyframe assets were generated or overwritten for this planning pass.
This is a reference for constructing a shot plan, not a validated finished edit.

Regenerate the gentle mix and maps with:

```bash
.runtime/venv/bin/python tools/prepare_natural_edit.py
```

The ASR estimates used by the script are saved in
`natural-pace-word-alignment.json` and cached under `.runtime/natural-plan/`.
They should be reviewed against actual hands/poses before committing keyframes.
"""
    (OUT / "NATURAL-PACE-VIDEO-PLAN.md").write_text(plan)


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    alignment_cache = WORK / "word-alignment.json"
    if not alignment_cache.exists():
        alignment_cache.write_bytes(
            (OUT / "natural-pace-word-alignment.json").read_bytes()
        )
    rows, metadata = audio_and_cues()
    anchors = action_anchors(rows)
    editing_plan(rows, metadata, anchors)
    print(json.dumps({"audio": metadata, "action_anchors": anchors}, indent=2))
