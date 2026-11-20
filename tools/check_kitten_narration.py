"""Independent word checks of the Kitten-generated script paragraphs."""

import argparse
import difflib
import hashlib
import json

from check_narration import words
from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio
from generate_narration import ROOT

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", type=int, nargs="+")
    parser.add_argument("--model", default="small.en")
    args = parser.parse_args()
    paragraphs = (
        (ROOT / "assets/relaxing-a-turkey-script.txt").read_text().strip().split("\n\n")
    )
    report = ROOT / "output/kitten-speech-check.json"
    results = json.loads(report.read_text()) if args.only and report.exists() else []
    model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=6)
    for i, expected in enumerate(paragraphs, 1):
        if args.only and i not in args.only:
            continue
        path = ROOT / f".runtime/kitten-narration/takes/{i:02}.wav"
        audio = decode_audio(str(path), sampling_rate=16000)
        peak = float(abs(audio).max())
        if peak > 0:
            audio *= 0.8 / peak
        segments, _ = model.transcribe(
            audio, language="en", beam_size=5, condition_on_previous_text=False
        )
        recognized = "".join(s.text for s in segments).strip()
        a, b = words(expected), words(recognized)
        delta = [
            {
                "operation": op,
                "expected": " ".join(a[s:e]),
                "recognized": " ".join(b[u:v]),
            }
            for op, s, e, u, v in difflib.SequenceMatcher(
                a=a, b=b, autojunk=False
            ).get_opcodes()
            if op != "equal"
        ]
        item = {
            "paragraph": i,
            "model": args.model,
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "expected": expected,
            "recognized": recognized,
            "differences": delta,
        }
        results = [r for r in results if r["paragraph"] != i] + [item]
        print(json.dumps(item), flush=True)
    report.write_text(
        json.dumps(sorted(results, key=lambda r: r["paragraph"]), indent=2) + "\n"
    )
