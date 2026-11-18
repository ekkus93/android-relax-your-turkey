# Relax Your Turkey

Thanksgiving parody narration generated locally with CosyVoice 3 from
`assets/relaxing-a-turkey-script.txt`, using `assets/my_clip.wav` as the voice
reference and the 20 windows in `assets/relaxing-a-turkey-timed-draft.md`.

- [Rebuilt WAV](output/relaxing-a-turkey-cleaned.wav) and [MP3](output/relaxing-a-turkey-cleaned.mp3): revised voice prompt and audio cleanup, with the same 99.614-second timeline. See [cleanup notes](output/CLEANUP.md).
- [Cleaned original reference](output/my_clip-cleaned.mp3) and [new CosyVoice test](output/cosyvoice-cleaned-clip-test.mp3): generated using a cleaned copy of `my_clip.wav` itself. The test has no timing compression or output denoising. See [reference cleanup notes](output/ORIGINAL-CLIP-CLEANUP.md).
- Full narration using that cleaned original: [natural pace](output/relaxing-a-turkey-from-cleaned-clip-natural.mp3), [99.614-second timed version](output/relaxing-a-turkey-from-cleaned-clip.mp3).
- [Original timed WAV](output/relaxing-a-turkey-timed.wav): 99.614 seconds, 48 kHz mono, 24-bit PCM.
- [MP3 preview](output/relaxing-a-turkey-preview.mp3).
- [Unfitted takes assembled as a WAV](output/relaxing-a-turkey-natural.wav).
- [Cue captions](output/relaxing-a-turkey.srt) and [timing measurements](output/timing-report.csv).
- [Production notes and regeneration commands](output/PRODUCTION.md).

The source script and timing draft are preserved. `output/takes/` contains the
native 24 kHz generated takes; `output/cues/` contains fitted 48 kHz clips with
the same gain as the timed master. Place the cue clips at the starts in the CSV.
