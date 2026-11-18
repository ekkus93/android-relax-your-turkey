# Relaxing a Turkey — dialogue draft v1

Full-length adaptation of the supplied 99.614-second source. This follows the user's request to adapt the original transcript; it is longer than the earlier proposed 30–45-second cut.

The source captions are automatic and contain garbled wording during the carving sequence. That section is rewritten for clear performance rather than treated as a verbatim transcription. Every spoken reference to the bird is now turkey. Thanksgiving jokes replace dialogue within existing beats.

## Recording guidance

- Read only the dialogue in `relaxing-a-turkey-script.txt`; do not speak timestamps or these notes.
- Aim for approximately 100 seconds overall, using the windows below as targets, not measured speech durations.
- Keep an upbeat cooking-show delivery. Leave small pauses for physical demonstrations and the joke about the main course.
- Follow the source rhythm closely for the massage, wing movements, nervous/relaxed demonstration, and countdown. The carving commentary is deliberately fast.
- A natural take is more useful than forcing every syllable into the source timing. Separate takes at paragraph boundaries give us editing flexibility. WAV is preferred; 48 kHz if available.
- Once the recorded voice is available, measure its actual timing and update the shot plan and captions. These windows are provisional, not final subtitles.

## Dialogue windows

| Source window | Dialogue |
| --- | --- |
| 00:00.440–00:04.760 | Watch. I need this ingredient in the fridge. |
| 00:04.760–00:09.480 | I have this beautiful turkey that I saved for Thanksgiving. And I'm going to |
| 00:09.480–00:14.800 | show you how to debone this turkey in eighteen seconds or less. Don't blink. |
| 00:14.800–00:16.280 | If you blink, I finished the turkey already, |
| 00:16.280–00:20.360 | okay? Because this is going to go well with the stuffing and cranberry sauce, |
| 00:20.360–00:23.960 | okay? Here, I have a beautiful turkey. |
| 00:23.960–00:30.680 | And this turkey is so huge, and it's so tense, you cannot cut through, even with a sharp knife. So, you've got to learn the |
| 00:30.680–00:38.120 | Chinese secret, which I learned from an elderly man in Chongqing, Sichuan. |
| 00:38.120–00:46.320 | He said, "First, relax the turkey." Of course he's nervous—it's Thanksgiving! Everybody's coming over for dinner, and he's the main course! |
| 00:46.320–00:52.160 | You use only three fingers. You go up and down, up and down, circular motion. |
| 00:52.160–00:56.760 | Only up and down. Don't waste time going sideways. Save your energy for the dishes. |
| 00:56.760–01:01.400 | Circular motion. And then you wing it, okay? You wing it. |
| 01:01.400–01:02.360 | And you know what? |
| 01:02.360–01:06.840 | The turkey is totally relaxed. Look at this. |
| 01:06.840–01:09.800 | Nervous. Relaxed. Ready for Thanksgiving. |
| 01:09.800–01:12.840 | Now, pay attention. Eighteen seconds. Time it, |
| 01:12.840–01:20.280 | okay? Three, two, one! One cut. Another cut. Turn it around. One cut along the back. Hold it like this. Don't do it like that. |
| 01:20.280–01:27.760 | The whole turkey breast comes out, and the tenderloin comes out like this. The tenderloin on this side comes out like that. Please, come out! |
| 01:27.760–01:37.200 | And turn it around. This side. The turkey breast comes out like this. Another piece of turkey breast comes out like that. And the last little tenderloin comes out like that. |
| 01:37.200–01:39.614 | Nice and done. Happy Thanksgiving! |

## Picture and audio workflow

1. Use the approved dialogue and recorded voice to establish actual phrase lengths before generating final video. Source timestamps remain an action reference.
2. Detect camera cuts and select additional action boundaries within long shots. Dialogue windows above are not automatically generation clip boundaries.
3. Extract source frames at those boundaries, plus reference frames where the hands or bird change pose substantially. Use decoded video frames, not codec keyframes selected only by encoding structure.
4. Edit every visible bird and carved piece to match one consistent plucked turkey. Maintain the kitchen, host, lighting, hands, utensils, contact shadows, and plausible relative scale. Approve a reference look before editing all frames.
5. Use edited opening and ending images with a model that accepts both. For adjacent clips within one continuous shot, reuse the same edited boundary image as the preceding clip's end and the next clip's start. Do not interpolate across a camera cut.
6. Generate manageable action segments, initially about 3–6 seconds where supported. Model duration limits may require longer takes trimmed to the edit. First/last frames constrain the endpoints; intermediate anatomy and action still need review, especially carving and hand contact.
7. Treat spoken mouth motion as a separate requirement. Either select a compatible workflow that accepts the recorded dialogue alongside the picture inputs or apply lip sync after picture generation. Verify the chosen model's exact input combinations before spending credits. Merely adding audio to a generated video will not synchronize the lips.
8. Assemble clips against the recorded voice, review joins at frame level, and add kitchen sounds or music separately. Avoid audible source dialogue underneath the new performance. Preserve usable original material only where the picture and changed speech fit.

Martini documents start-frame and end-frame support as model-dependent: https://www.martini.film/docs/generation/video

No audio or video generation has been submitted for this draft.
