# Light texture smoothing

This pass starts with the latest `relaxing-a-turkey-natural-gentle.wav` and
targets the remaining fine, scratchy/static-like texture. The voice takes,
reference, speaking pace and gaps are unchanged. No new speech is synthesized.

## Listen

- `cosyvoice-smoothing-before-after.mp3`: the same joke passage before and after
  smoothing, in that order, with 750 ms of silence between the two. Both use
  their actual master volume; there is no separate gain boost for the new sample.
- `cosyvoice-my_clip2-smooth-test.mp3` / `.wav`: the smoothed passage alone.
- `relaxing-a-turkey-natural-smooth.mp3` / `.wav`: full 143.150-second master.
- `relaxing-a-turkey-natural-smooth.srt`: captions copied from the natural edit.

WAVs are 48 kHz mono, 24-bit PCM; MP3s are 192 kbps listening copies. Use the
WAV master for the video edit. The existing natural cue map, word/action anchors
and keyframe plan still apply.

## Processing

One [FFmpeg non-local-means pass](https://ffmpeg.org/ffmpeg-filters.html#anlmdn)
compares nearby audio contexts to reduce broadband noise. The settings are
`anlmdn=s=1:p=0.002:r=0.012:m=8`. The result is blended 75% processed / 25%
original to retain articulation and vocal texture. It is not another round of
voice cloning, impulse repair, compression, loudness normalization or EQ.

The selected pass keeps the original sample count and checks alignment in
three voiced sections. No pitch/time changes or low-pass filter are applied.
Gain can only stay unchanged or decrease if necessary to retain peak headroom;
in this render no additional attenuation was needed.

Measured changes over the full track:

- RMS level: -0.014 dB, so the comparison is essentially level matched.
- 200 Hz–1 kHz energy: -0.006 dB.
- 2.5–4 kHz energy: -0.362 dB.
- 4–8 kHz energy: -0.510 dB.
- Sample peak remains approximately -5.45 dBFS.

These checks limit broad tonal/level changes; they do not prove that every
audible artifact is gone. Synthetic vocal grain can resemble noise, and
stronger smoothing can remove consonant detail. This is a conservative listening
candidate that preserves the prior mix separately.

`smoothing-report.json` contains source/output hashes, parameters and checks.
`smoothing-speech-check.json` records a transcription check of the short sample.

Regenerate from the accepted gentle master:

```bash
.runtime/venv/bin/python tools/smooth_narration.py
```
