# Word-specific hiss and tonal balance

This listening candidate starts with `relaxing-a-turkey-natural-smooth.wav`.
It aims to soften high-frequency bursts on particular syllables while giving
the voice a little more low-frequency body and mid/high presence. The selected
voice takes, script, 143.150-second natural pace and keyframe map are unchanged.

## Sample rate versus frequency balance

The exported WAV is 48 kHz mono, 24-bit PCM. Its MP3 copy is also 48 kHz mono,
at 192 kbps. CosyVoice's native generated speech is **24 kHz**, and is upsampled
for the 48 kHz video masters. The supplied `my_clip2.wav` is 48 kHz.

The output sample rate is not a description of the frequencies actually present
in the voice. Upsampling does not restore missing detail, and a narrow-sounding
voice is not proof of a low export sample rate. A 24 kHz signal can carry a
much wider range than traditional telephone speech. The earlier 8 kHz reference
is no longer used; this candidate still uses the voice generated from `my_clip2.wav`.

## Listen

- `cosyvoice-hiss-before-after.mp3`: the previous smoothed passage first, then
  this de-essed/balanced passage, separated by 750 ms of silence. It uses each
  master's actual playback level.
- `cosyvoice-my_clip2-balanced-test.mp3` / `.wav`: the updated passage alone.
- `relaxing-a-turkey-natural-balanced.mp3` / `.wav`: the full natural master.
- `relaxing-a-turkey-natural-balanced.srt`: unchanged natural captions.

Use the WAV master for editing. No video retiming is required for this pass.

## Processing

The [FFmpeg crossover](https://ffmpeg.org/ffmpeg-filters.html#acrossover) separates
the signal around 4.5 kHz. Only the upper band receives soft-knee
[compression](https://ffmpeg.org/ffmpeg-filters.html#acompressor), so strong
high-frequency bursts are reduced while quieter upper-band detail is retained.
This is a split-band de-essing treatment, not a permanent high-frequency cut.

Upper-band settings are threshold 0.0125, ratio 3:1, attack 1 ms, release 70 ms,
no makeup gain and a 65% compressor mix. The band is recombined at unity gain.
A broad 1.5 dB low shelf at 180 Hz and a broad 1.5 dB presence boost at 2.6 kHz
follow. Overall gain is reduced slightly for level/peak matching; no new
wideband noise suppression, low-pass filter or peak limiter is added.

On this track, 620 of 14,315 ten-millisecond frames show more than 0.5 dB of
high-band reduction. Within those frames, median reduction is about 1.84 dB;
maximum measured active-frame reduction is about 4.34 dB. These are detector
measurements, not confirmed descriptions of every hiss the listener hears.

Relative to 300 Hz–1 kHz, energy at 80–220 Hz rises about 1.05 dB, at
1.5–3.5 kHz rises about 1.04 dB, and at 4.5–10 kHz falls about 1.02 dB.
Overall RMS level changes by only -0.062 dB, and the sample peak stays near
-5.45 dBFS. The same sample count is retained; checked waveform alignment shifts
are about 0.083 ms. The existing caption and action timings remain applicable.

The treatment cannot reconstruct detail absent from the synthesized voice.
Sibilance is a plausible explanation for word-specific hiss, but an automated
filter/measurement does not establish the audible cause or guarantee the result.
The preceding version remains available for comparison.

## Records and regeneration

`deessing-report.json` records the source/output hashes, sample rates, filter
graph, high-band detector measurements and timing checks.
`deessing-speech-check.json` records an independent word check of the sample.
Intermediate band signals are saved under `.runtime/deessing-v8/`.

```bash
.runtime/venv/bin/python tools/balance_narration.py
```
