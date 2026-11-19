# Natural narration: audio master and picture timing

The accepted natural narration remains **143.150 seconds
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
-5.45 dBFS. It does not boost treble, denoise
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
| 9 | 00:38.120 | 00:56.050 | Main-course joke |
| 10 | 00:46.320 | 01:05.155 | Three-finger massage |
| 12 | 00:56.760 | 01:19.965 | Wing movement |
| 15 | 01:06.840 | 01:33.270 | Nervous / relaxed poses |
| 16 | 01:09.800 | 01:36.115 | Pay attention / eighteen seconds |
| 17 | 01:12.840 | 01:41.350 | Countdown lead-in |
| 20 | 01:37.200 | 02:19.825 | Finished turkey / Thanksgiving greeting |

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

The natural first-cut call is approximately **01:46.230**; the final
tenderloin commentary ends around **02:19.580**. That span is about
**33.4 seconds**, not 18 seconds. These are speech anchors,
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
