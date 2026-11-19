# Crackle repair and presence adjustment

This pass processes the existing, accepted narration generated from the cleaned
`my_clip.wav` reference. It does not regenerate speech, change the reference,
edit words, or change the timing. Earlier exports remain available.

## Listening copies

- `cosyvoice-polished-test.mp3` / `.wav`: balanced presence adjustment of the
  same 9.760-second test passage.
- `cosyvoice-brighter-test.mp3` / `.wav`: a stronger presence/treble adjustment
  of that passage for comparison.
- `relaxing-a-turkey-polished-natural.mp3` / `.wav`: balanced treatment of the
  123.135-second natural-pace narration.
- `relaxing-a-turkey-polished-timed.mp3` / `.wav`: balanced treatment of the
  99.614-second timed narration. Its existing captions remain applicable.

All new WAVs are 48 kHz mono, 24-bit PCM. MP3 copies use 192 kbps. Both test
presets are normalized to approximately -18 LUFS with a -2 dBTP ceiling, so
the comparison is not driven by one version simply being louder.

## Treatment

One conservative FFmpeg `adeclick` pass precedes EQ: 30 ms analysis window,
75% overlap, autoregression order 2, threshold 5, burst fusion 1. The filter
reports 31 detected impulse samples in the short test, 202 in the natural
narration and 104 in the timed narration. These are detector counts, not
confirmed audible crackles or a measure of perceived quality. Consonants and
glottal voice sounds can resemble impulses; the pass is intentionally light.
No additional broadband denoising or low-pass filtering is applied.

The balanced EQ uses:

- A broad 1 dB cut at 350 Hz to reduce low-mid dominance.
- A broad 2.5 dB boost at 2.2 kHz for presence.
- A 3 dB high shelf centered at 3 kHz for treble.

The brighter test increases the presence boost to 3.5 dB and the shelf to 5 dB.
Measured energy at 2.5–4 kHz relative to 200 Hz–1 kHz rises by about 4.4 dB
in the balanced test and 6.2 dB in the brighter test. The full balanced tracks
show a similar change of about 4.2–4.3 dB.

The original 8 kHz reference has a limited frequency range, and the accepted
generated speech also has little energy above 4 kHz. EQ can make the existing
speech brighter but cannot recover detail absent from the original recording.
Increasing the shelf further could emphasize residual artifacts as well as
speech, so the stronger setting is initially provided as a short comparison.

Processing uses float intermediates, then two-pass loudness normalization.
The peak ceiling can require dynamic normalization; the report records the
actual mode used. Duration and alignment are checked against the source.
Measured alignment shifts are below 0.1 ms in the test and zero in the full
tracks. No speech is trimmed to force these checks to pass.

## Records

`polishing-report.json` contains source/output hashes, filter parameters,
detector counts, normalization results and timing checks.
`polishing-speech-check.json` contains an independent transcription check of
both short presets. Neither waveform checks nor transcription establish how
natural or crackle-free the result sounds; these exports are for listening
comparison.

Regenerate from the accepted exports:

```bash
.runtime/venv/bin/python tools/polish_narration.py
```
