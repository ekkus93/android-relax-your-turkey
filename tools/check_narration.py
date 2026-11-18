"""Transcribe each cue as a content check; ASR differences need human review."""

import argparse
import difflib
import json
import re

from faster_whisper import WhisperModel
from generate_narration import OUT, cues


def words(text):
    text = re.sub(r"\b18\b", "eighteen", text)
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower().replace("’", "'"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fitted", action="store_true")
    parser.add_argument("--only", type=int, nargs="+")
    args = parser.parse_args()
    model = WhisperModel("small.en", device="cpu", compute_type="int8", cpu_threads=6)
    suffix = "fitted" if args.fitted else "natural"
    report_path = OUT / f"asr-check-{suffix}.json"
    results = (
        json.loads(report_path.read_text())
        if args.only and report_path.exists()
        else []
    )
    for cue in cues():
        if args.only and cue["id"] not in args.only:
            continue
        path = OUT / ("cues" if args.fitted else "takes") / f"{cue['id']:02}.wav"
        segments, _ = model.transcribe(
            str(path), language="en", beam_size=5, condition_on_previous_text=False
        )
        transcript = "".join(s.text for s in segments).strip()
        expected, actual = words(cue["text"]), words(transcript)
        differences = [
            {
                "operation": op,
                "expected": " ".join(expected[a:b]),
                "recognized": " ".join(actual[c:d]),
            }
            for op, a, b, c, d in difflib.SequenceMatcher(
                a=expected, b=actual, autojunk=False
            ).get_opcodes()
            if op != "equal"
        ]
        result = {
            "id": cue["id"],
            "expected": cue["text"],
            "recognized": transcript,
            "differences": differences,
        }
        results = [r for r in results if r["id"] != cue["id"]] + [result]
        print(json.dumps(result), flush=True)
    report_path.write_text(json.dumps(sorted(results, key=lambda r: r["id"]), indent=2))
