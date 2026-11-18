# Revised narration

`relaxing-a-turkey-cleaned.wav` and `relaxing-a-turkey-cleaned.mp3` are a new
generation and mix addressing the reported scratchiness and popping. The
original export remains available for comparison. The revised WAV is 48 kHz,
mono, 24-bit PCM and exactly 99.614 seconds long. Its cue captions are in
`relaxing-a-turkey-cleaned.srt`.

The original generated takes contain 682 samples at the vocoder's 0.99 hard
clamp threshold. Turning down the finished mix cannot restore those flattened
peaks. The original reference also contains only 8 kHz audio. Both are possible
contributors to the reported roughness; these measurements alone do not
establish every audible artifact's cause.

The supplied `my_clip.wav` matches a passage in the supplied source video with
0.99266 normalized correlation, beginning at 39.649125 seconds. The revised
generation uses the same voice and passage, recovered from that video's
44.1 kHz AAC audio rather than the 8 kHz copy. The prompt begins at 40.249125
seconds and lasts 4.60 seconds. It is converted to 24 kHz mono and filtered at
65 Hz. The matching prompt transcript is unchanged.

CosyVoice 3 inference runs in full precision, with the vocoder hard clamp
disabled and floating-point intermediates. None of the new raw takes reaches
the old 0.99 clamp threshold. The mix applies conservative impulse repair,
4 dB of FFT noise reduction, a 70 Hz high-pass and a 7.2 kHz low-pass. Only
takes that exceed their timing windows are sped up; shorter takes retain their
natural rate. FFmpeg's `atempo` filter fits the long takes. Rubber Band's
smoothing option produced spikes during validation and is excluded; other
Rubber Band settings also produced less reliable speech recognition in long
cues, so the revised mix uses `atempo` instead.
The render rejects filter outputs whose peaks exceed twice the input peak.

Cue edges have 12 ms fades. Two-pass dynamic loudness normalization targets
-18 LUFS and a -2 dBTP ceiling, keeping speech at a useful listening level with
headroom for encoding. The normalization was checked for timing shifts.

`cleanup-report.json` records the source offset, per-cue synthesis seeds,
instruction modes, speed changes, filters and WAV checksum. Intermediate takes
and fitted cues are kept under the ignored `.runtime/clean-v2/` directory.
The script and upstream model revision are the same as in `PRODUCTION.md`.
Automated speech checks are saved in `asr-check-cleaned.json`; the diagnostic
audio is normalized before transcription so quiet raw takes are not treated as
silence. Automated checks do not establish perceived voice quality; this is a
comparison version for listening review.

The small.en recognizer flags four cues. A second check with medium.en verifies
the full `Only up and down` and `Nervous` lines that small.en omitted. Both
recognizers omit the leading `okay?` in cue 5 and `And` in cue 7; these remain
minor wording uncertainties for listening review. The secondary results are
saved in `asr-check-cleaned-secondary.json`. The final WAV measures -18.1 LUFS
and -2.0 dBTP, and the rendered cue windows and 99.614-second duration pass the
timing checks.

Regenerate in the existing workspace:

```bash
.runtime/venv/bin/python tools/improve_narration.py
.runtime/venv/bin/python tools/improve_narration.py --only 4 8 18 --seed-offset 200
.runtime/venv/bin/python tools/check_narration.py --fitted --directory .runtime/clean-v2
```

The first command resumes existing takes; use `--only` to explicitly replace
selected takes. To repeat only the filters and mix, run:

```bash
.runtime/venv/bin/python tools/improve_narration.py --render-only
```
