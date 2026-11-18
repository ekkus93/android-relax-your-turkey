# CosyVoice using the cleaned original WAV

This attempt cleans `assets/my_clip.wav` itself before passing it to CosyVoice.
No audio from the source video is used in this attempt. The original WAV is
unchanged. The existing exports are kept separately.

## Listen

- `my_clip-cleaned.mp3`: the cleaned 12.266375-second original recording.
- `my_clip-cleaned.wav`: its 48 kHz mono, 24-bit WAV master.
- `my_clip-cleaned-prompt.wav`: the exact 24 kHz prompt sent to CosyVoice,
  cut from 6.55 through 12.10 seconds of the cleaned reference.
- `cosyvoice-cleaned-clip-test.mp3` / `.wav`: a short generated joke passage.
  This sample has no time stretching, noise filtering or loudness compression
  after synthesis. Only its overall volume is adjusted to a -2 dBFS sample peak.
- `relaxing-a-turkey-from-cleaned-clip-natural.mp3` / `.wav`: all generated
  takes in script order at their natural speaking rate, with 150 ms between
  cues. This version exceeds the original video duration.
- `relaxing-a-turkey-from-cleaned-clip.mp3` / `.wav`: the 99.614-second edit
  with each take fitted to its source window. Captions use the same stem with
  an `.srt` extension.

The short test reads:

> He said, "First, relax the turkey." Of course he's nervous—it's Thanksgiving!
> Everybody's coming over for dinner, and he's the main course!

The test and natural version separate the generated voice from artifacts that
may arise when fitting speech to tight windows. These are listening candidates;
signal and transcription checks do not establish how natural the voice sounds.
The natural narration is 123.135 seconds; the short test is 9.760 seconds.
The timed version still speeds up several cues substantially. Its automated
transcription check flags `the turkey` in cue 4 and the opening `And` in cue 19;
the remaining cues match after punctuation/case/number normalization. See
`asr-check-original-clip.json`. The reference cleanup and prompt transcript were
also checked with a separate recognizer.

## Reference treatment

The 8 kHz stereo recording is converted to mono and resampled to 48 kHz for
the denoiser. A 65 Hz high-pass and conservative impulse repair run before any
gain increase. The repaired recording is peak-scaled to 0.7, then passed through
FFmpeg's `arnndn` speech denoiser using the pinned
[somnolent-hogwash RNNoise model](https://github.com/GregorR/rnnoise-models/tree/3eee541a283fd3b8f81b85b1748e3b9ccbefa04d/somnolent-hogwash-2018-09-01).
The wet mix is 75%, retaining some original signal to limit excessive suppression.
A 3.7 kHz low-pass follows; resampling does not recover bandwidth absent from
the original recording.

All restoration intermediates are floating-point WAVs to avoid clipping.
The denoiser's measured 10 ms delay is compensated. The cleaned clip retains
the original duration and its alignment was checked by correlation. Its gain
targets -22 dBFS RMS with a -3 dBFS peak ceiling. The extracted prompt has the
matching transcript:

> You use only three finger. You go up and down, up and down, circular motion.

CosyVoice 3 uses zero-shot synthesis for every cue, including the short lines;
no fast-speech instruction mode is used. Generation runs in full precision
with unclamped floating-point vocoder output. There is no noise filtering of
the generated narration in this attempt. The timed export uses `atempo` only
when a take overruns its window, with factors no greater than 2 per stage,
12 ms fades at cue edges, and loudness normalization with a -2 dBTP ceiling.

## Records and regeneration

`original-clip-restoration.json` records the source and denoiser hashes,
reference processing and exact prompt. `original-clip-narration-report.json`
records the selected generation seeds, speed changes and timed WAV hash.
Intermediate native takes are in `.runtime/clean-v3-original/`. The model and
runtime versions are those documented for the previous narration.

```bash
.runtime/venv/bin/python tools/improve_narration.py --clean-original --seed-offset 3000
.runtime/venv/bin/python tools/check_narration.py --fitted --directory .runtime/clean-v3-original
```

The generation command resumes existing takes; use `--only` with cue numbers
to explicitly replace takes. To repeat only the assembly, run:

```bash
.runtime/venv/bin/python tools/improve_narration.py --clean-original --render-only
```
