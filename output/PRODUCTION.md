# Narration production

AI-generated parody narration using the supplied voice reference. Each cue is
generated from the script; the timing draft supplies 20 cue windows.
Neither input text file was edited. No original video dialogue was mixed into
the result.

## Deliverables

- `relaxing-a-turkey-timed.wav`: 99.614 seconds, 48 kHz, mono, 24-bit PCM.
  Every cue starts at its draft timestamp and finishes within its window.
- `relaxing-a-turkey-preview.mp3`: 192 kbps listening copy of the timed master.
- `relaxing-a-turkey-natural.wav`: the selected takes in script order without
  time stretching; adds 120 ms between cues. This version does not follow the
  video timestamps.
- `takes/01.wav` through `20.wav`: original selected synthesized takes at 24 kHz.
- `cues/01.wav` through `20.wav`: fitted clips, 48 kHz, with master gain applied.
- `relaxing-a-turkey.srt`: cue captions using the draft starts and rendered cue
  ends. These are cue-level captions, not word-level forced alignment.
- `timing-report.csv`, `cues.json`: source windows, take durations, applied tempo
  multipliers, and rendered cue ends. A multiplier above 1 speeds up a take.
- `asr-check-fitted.json`: independent faster-whisper small.en transcription
  comparisons against the script, with punctuation/case/18 normalized.
  Transcription is an automated content check, not a listening assessment.
- `audio-environment.txt`: principal package versions used locally.
- `generation-manifest.json`: source hashes, software/model revisions, take
  seeds and output measurements.

## Timing and quality

The final transcription check matches 19 of 20 cues after normalization. In
cue 19 (87.760–97.200 seconds), it omits the opening `And`, recognizes `This
side` as `the side`, and omits `the` before `last little tenderloin`. These may
be synthesis or recognition errors; review this cue by ear before locking the
video. A separate pickup of `And` is present in the take despite the ASR
omission. Listening quality and speaker similarity have not been assessed by
a human. Treat this export as a timed audio draft.

Synthesis uses FunAudioLLM/Fun-CosyVoice3-0.5B-2512 with the upstream CosyVoice
implementation. Standard takes use zero-shot synthesis. Cues 4 and 20 use its
fast-speech instruction mode with the same voice reference to reduce the amount
of stretching needed. Cue 3 uses the pronunciation spelling `de-bone`; cue 19
uses a separately synthesized pickup of its opening `And`. Spoken words and
caption text retain the supplied script.

The supplied reference is 8 kHz stereo and 12.266375 seconds long. A copy was
converted to 24 kHz mono, high-pass filtered at 70 Hz, and amplified by 8. The
prompt is the 4.60-second section beginning at 0.60 seconds. Upsampling does not
recover detail absent from the recording, so this reference limits voice fidelity.

The fitter trims only leading/trailing silence, retains a 35 ms margin, and uses
FFmpeg's Rubber Band filter for pitch-preserving speed changes. Takes shorter
than their windows are slowed by at most 15%, with remaining time left silent.
Long takes are sped up to fit, so the countdown and carving delivery is brisk.
Speech is not cut off to force a fit. The master has 440 ms of opening silence,
short fades at cue edges, and a sample peak normalized to -1 dBFS. Cue clips
use the same gain, so they can reconstruct the master at their CSV starts.

## Regenerating in this workspace

The ignored `.runtime/` directory holds the checkout, virtual environment,
model weights, processed reference, render intermediates and diagnostic logs.
The base Python supplies CUDA-enabled PyTorch and torchaudio; synthesis runs
on the local RTX 4070 Ti SUPER. The source is
https://github.com/FunAudioLLM/CosyVoice and the model is
https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512 .

To reassemble existing selected takes:

```bash
.runtime/venv/bin/python tools/generate_narration.py --assemble-only
ffmpeg -y -i output/relaxing-a-turkey-timed.wav -c:a libmp3lame -b:a 192k output/relaxing-a-turkey-preview.mp3
```

The generator resumes by skipping existing takes. `--only` explicitly replaces
the selected takes. To recreate the selected generation choices, start with an
empty `output/takes/` directory (preserve an existing export first), then run:

```bash
.runtime/venv/bin/python tools/generate_narration.py
.runtime/venv/bin/python tools/generate_narration.py --only 2 7 --seed-offset 200
.runtime/venv/bin/python tools/generate_narration.py --only 3 --seed-offset 400
.runtime/venv/bin/python tools/generate_narration.py --only 4 20 --fast --seed-offset 100
.runtime/venv/bin/python tools/generate_narration.py --only 19 --seed-offset 500
.runtime/venv/bin/python tools/check_narration.py --fitted
```

Base seed is 20261118 plus cue number plus seed offset. GPU inference can vary
slightly across software or hardware changes. Regenerate the MP3 after changing
the WAV. Do not reuse old takes after changing script words; the fitter checks
that the timing table and script agree but does not invalidate cached takes.
