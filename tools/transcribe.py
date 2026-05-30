"""Offline voice-note transcription for Telegram audio — no API key, fully local.

Uses faster-whisper (CTranslate2). First run downloads the model (~150 MB for
"base", cached under ~/.cache/huggingface afterwards). Decodes ogg/oga/mp3/wav
directly via PyAV — no ffmpeg pre-convert needed.

Usage:
    python tools/transcribe.py <audio_path> [--model base|small|medium] [--lang en]

Prints the plain transcript to stdout (nothing else), so a caller can capture it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from faster_whisper import WhisperModel

# CPU int8 is fast + accurate enough for speech notes; no GPU assumed.
_COMPUTE = "int8"


def transcribe(audio_path: str, model_size: str = "base", lang: str | None = None) -> str:
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"audio not found: {path}")
    model = WhisperModel(model_size, device="cpu", compute_type=_COMPUTE)
    segments, _info = model.transcribe(str(path), language=lang, vad_filter=True)
    return " ".join(seg.text.strip() for seg in segments).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--model", default="base")
    ap.add_argument("--lang", default=None)
    args = ap.parse_args()
    sys.stdout.write(transcribe(args.audio, args.model, args.lang))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
