# Narration using my_clip2.wav

This generation uses only the newly supplied `assets/my_clip2.wav` as its
voice reference. The earlier reference files and narration exports are preserved.

## Listen

- `cosyvoice-my_clip2-test.mp3` / `.wav`: the same joke passage used for previous
  voice comparisons, generated with the new reference. There is no time fitting,
  EQ, denoising or loudness compression on this sample. Its overall gain is
  adjusted to a -2 dBFS sample peak.
- `relaxing-a-turkey-my_clip2-natural.mp3` / `.wav`: the full narration at the
  generated speaking rate, with 150 ms gaps between cues. No time stretching
  or EQ is applied. The track exceeds the video's duration.
- `relaxing-a-turkey-my_clip2.mp3` / `.wav`: the 99.614-second timed edit, with
  cue captions in `relaxing-a-turkey-my_clip2.srt`. Long takes are fitted with
  FFmpeg `atempo` in stages no greater than 2x. Some cues require substantial
  speed increases, so the short test and natural track are better for judging
  the new voice independently of timing adjustments.

The new full WAVs are 48 kHz, mono, 24-bit PCM; the unprocessed voice test is
native 24 kHz, mono, 24-bit PCM. MP3 copies use 192 kbps.

## Prompt and generation

The new source is 48 kHz stereo, 12.973250 seconds long. Reference preparation
uses mono conversion and resampling to 24 kHz. No noise suppression, EQ or
narrowband low-pass filter is applied to this reference. A complete 4.9-second
sentence is selected from 4.85 through 9.75 seconds:

> Somehow my mother never get out of work until probably about six thirty or seven.

`my_clip2-prompt.wav` is the exact prompt passed to CosyVoice, and
`my_clip2-prompt.txt` contains the corresponding spoken transcript. A separate
recognizer checked the selected sentence. `my_clip2-reference-transcript.json`
records the source transcription and word timing used to choose the interval.
`my_clip2-reference.json` records both source and prompt SHA-256 hashes and
the preparation parameters.

Generation uses the existing CosyVoice 3 model and runtime, full precision,
zero-shot mode, and floating-point vocoder output without the default hard
clamp. Base seed is 20261118 plus cue number plus 4000. Cue 9 uses offset 5000
for a replacement take. The script's em dash is spoken as a sentence break;
spoken words remain based on the supplied script.

The timed master includes 12 ms edge fades and two-pass loudness normalization
targeting -18 LUFS and a -2 dBTP ceiling. The report records its actual filters,
generation settings and WAV hash. These checks do not establish how natural
or artifact-free the voice sounds; this is a new listening comparison.

The short test is 9.040 seconds; the natural narration is 143.150 seconds.
Both recognizers match the short test's words after punctuation/case
normalization. The timed transcription check flags the opening `And` in cues
7 and 19, and `you` versus `you'll` in cue 10. These remain wording uncertainties
for listening review. Results are in `my_clip2-speech-check.json` and
`my_clip2-test-speech-check.json`.

## Regenerate

```bash
.runtime/venv/bin/python tools/improve_narration.py --reference-wav assets/my_clip2.wav --reference-text-file output/my_clip2-prompt.txt --prompt-start 4.85 --prompt-duration 4.9 --seed-offset 4000
.runtime/venv/bin/python tools/improve_narration.py --reference-wav assets/my_clip2.wav --reference-text-file output/my_clip2-prompt.txt --prompt-start 4.85 --prompt-duration 4.9 --seed-offset 5000 --only 9
.runtime/venv/bin/python tools/check_narration.py --fitted --directory .runtime/my_clip2-generation
```

Intermediate takes are cached in `.runtime/my_clip2-generation/`. The first
command resumes existing takes; `--only` replaces specified takes. A changed
reference or prompt is rejected when incompatible takes remain cached. Use
`--render-only` with the same reference arguments to reassemble existing takes.
