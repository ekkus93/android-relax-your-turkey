# Relax Your Turkey

Thanksgiving parody narration generated locally with CosyVoice 3 and Kitten TTS 2 from
`assets/relaxing-a-turkey-script.txt`, using the supplied voice references
and the 20 windows in `assets/relaxing-a-turkey-timed-draft.md`.
Both engines generate speech at 24 kHz; the full video-edit WAV masters are
exported at 48 kHz. Upsampling does not recreate missing frequency detail.

- Kitten TTS 2 trial: [voice sample](output/kitten-tts-voice-test.mp3), [volume-matched CosyVoice/Kitten comparison](output/cosyvoice-vs-kitten.mp3), [full natural narration](output/relaxing-a-turkey-kitten-natural.mp3), [WAV master](output/relaxing-a-turkey-kitten-natural.wav). The comparison plays the latest balanced CosyVoice mix first and Kitten second.
- Latest reference, `my_clip2.wav`: [voice test](output/cosyvoice-my_clip2-test.mp3), [natural narration](output/relaxing-a-turkey-my_clip2-natural.mp3), [timed narration](output/relaxing-a-turkey-my_clip2.mp3). See [sample 2 notes](output/MY_CLIP2.md).
- Natural-pace edit option: [gentler mix](output/relaxing-a-turkey-natural-gentle.mp3), [WAV master](output/relaxing-a-turkey-natural-gentle.wav), [natural timing and keyframe plan](output/NATURAL-PACE-VIDEO-PLAN.md), [cue map](output/natural-pace-cue-map.csv). Same 143.150-second pacing, with softer peaks and extra headroom.
- Light texture smoothing of the gentle mix: [before/after comparison](output/cosyvoice-smoothing-before-after.mp3), [smoothed sample](output/cosyvoice-my_clip2-smooth-test.mp3), [full natural narration](output/relaxing-a-turkey-natural-smooth.mp3), [WAV master](output/relaxing-a-turkey-natural-smooth.wav). The natural timing map is unchanged. See [smoothing notes](output/SMOOTHING.md).
- Selective hiss control and tonal balancing: [before/after](output/cosyvoice-hiss-before-after.mp3), [voice sample](output/cosyvoice-my_clip2-balanced-test.mp3), [full natural narration](output/relaxing-a-turkey-natural-balanced.mp3), [WAV master](output/relaxing-a-turkey-natural-balanced.wav). Same 143.150-second timing. See [de-essing and sample-rate notes](output/DEESSING.md).
- [Rebuilt WAV](output/relaxing-a-turkey-cleaned.wav) and [MP3](output/relaxing-a-turkey-cleaned.mp3): revised voice prompt and audio cleanup, with the same 99.614-second timeline. See [cleanup notes](output/CLEANUP.md).
- [Cleaned original reference](output/my_clip-cleaned.mp3) and [new CosyVoice test](output/cosyvoice-cleaned-clip-test.mp3): generated using a cleaned copy of `my_clip.wav` itself. The test has no timing compression or output denoising. See [reference cleanup notes](output/ORIGINAL-CLIP-CLEANUP.md).
- Full narration using that cleaned original: [natural pace](output/relaxing-a-turkey-from-cleaned-clip-natural.mp3), [99.614-second timed version](output/relaxing-a-turkey-from-cleaned-clip.mp3).
- Presence/treble adjustment of the same accepted voice: [balanced test](output/cosyvoice-polished-test.mp3), [brighter test](output/cosyvoice-brighter-test.mp3), [full natural version](output/relaxing-a-turkey-polished-natural.mp3), [full timed version](output/relaxing-a-turkey-polished-timed.mp3). See [mastering notes](output/POLISHING.md).
- [Original timed WAV](output/relaxing-a-turkey-timed.wav): 99.614 seconds, 48 kHz mono, 24-bit PCM.
- [MP3 preview](output/relaxing-a-turkey-preview.mp3).
- [Unfitted takes assembled as a WAV](output/relaxing-a-turkey-natural.wav).
- [Cue captions](output/relaxing-a-turkey.srt) and [timing measurements](output/timing-report.csv).
- [Production notes and regeneration commands](output/PRODUCTION.md).

The source script and timing draft are preserved. `output/takes/` contains the
native 24 kHz generated takes; `output/cues/` contains fitted 48 kHz clips with
the same gain as the timed master. Place the cue clips at the starts in the CSV.

## Kitten comparison

This trial uses [Kitten TTS 2](https://github.com/KittenML/KittenTTS) with
`my_clip2.wav` as the cloning reference. An 8.12325-second excerpt beginning at
4.85 seconds contains two complete sentences; its exact waveform/transcript are
saved as `kitten-my_clip2-reference.wav` / `.txt`. Preparation only converts to
mono and resamples. The model revision and source package commit are pinned in
`kitten-generation.json` and `tools/requirements-kitten.txt`.

Generation uses the stable preset, losslessly packed language-model weights
and the stock decoder. It reads the 15 approved script paragraphs at natural
speed. No timing compression, output EQ, noise reduction or dynamic limiter is
applied. Short edge fades, 150 ms gaps and a single global gain leave the WAV
peak at -5.5 dBFS. It is intentionally not pushed to a loudness target.

The full read is **108.125 seconds (1:48.125)**. It has its own
[paragraph captions](output/relaxing-a-turkey-kitten-natural.srt),
[paragraph timing map](output/kitten-natural-timing.csv) and
[action reference map](output/kitten-action-timing.csv). The earlier 143.15-second
CosyVoice map does not describe this take. Action positions are paragraph-level
planning anchors and require visual/word-level review before final keyframes.

The comparison attenuates only the louder excerpt to match integrated loudness;
the underlying full exports remain unchanged. Waveform and speech checks support
review but do not establish perceived fidelity or naturalness. Independent
transcriptions are saved in `kitten-speech-check.json` and
`kitten-test-speech-check.json`.
The smaller recognizer omits the opening "He said" in paragraph 5; the larger
recognizer includes it in the same take. That discrepancy is preserved in the
reports for listening review.

To regenerate in the existing workspace:

```bash
.runtime/kitten-venv/bin/python tools/generate_kitten_narration.py
.runtime/venv/bin/python tools/check_kitten_narration.py
```

The generator resumes cached paragraphs in `.runtime/kitten-narration/takes/`;
`--only` with paragraph numbers replaces selected takes, and `--seed-offset`
changes their seeds. `--assemble-only` rebuilds the exports without inference.
For a fresh setup, install `tools/requirements-kitten.txt` into an isolated
Python environment with a suitable PyTorch build; the generator downloads the
pinned model and the decoder's supporting weights on first use.
