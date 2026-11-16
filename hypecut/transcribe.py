"""Whisper transcription with word timings. Backends: faster-whisper (default) or whisper.cpp CLI."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import Settings


@dataclass
class Word:
    start: float
    end: float
    text: str


_FW_MODEL = None


def extract_wav(src: str, start: float, dur: float, out: Path) -> Path:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-vn", "-i", src,
                    "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(out)], check=True)
    return out


def transcribe(wav: Path, s: Settings) -> list[Word]:
    """Return word list with times relative to the wav start."""
    if s.whisper_cpp:
        return _whisper_cpp(wav, s)
    try:
        return _faster_whisper(wav, s)
    except ImportError:
        print("[whisper] faster-whisper not installed and no --whisper-cpp given: skipping transcript")
        return []


def _faster_whisper(wav: Path, s: Settings) -> list[Word]:
    global _FW_MODEL
    from faster_whisper import WhisperModel  # type: ignore

    if _FW_MODEL is None:
        print(f"[whisper] loading faster-whisper '{s.whisper_model}' (first run downloads it)")
        _FW_MODEL = WhisperModel(s.whisper_model, device="auto", compute_type="int8")
    segs, _ = _FW_MODEL.transcribe(str(wav), language=s.language, word_timestamps=True, vad_filter=True)
    words = []
    for seg in segs:
        for w in seg.words or []:
            words.append(Word(float(w.start), float(w.end), w.word.strip()))
    return [w for w in words if w.text]


def _whisper_cpp(wav: Path, s: Settings) -> list[Word]:
    model = s.whisper_model
    if not model.endswith(".bin"):
        raise SystemExit("With --whisper-cpp, pass --whisper-model path/to/ggml-*.bin")
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "out"
        cmd = [s.whisper_cpp, "-m", model, "-f", str(wav), "-ml", "1", "-sow", "-oj", "-of", str(base), "-np", "-t", str(max(os.cpu_count() or 4, 4)),
               "-l", s.language or "auto"]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        data = json.loads(Path(str(base) + ".json").read_text(encoding="utf-8", errors="replace"))
    words = []
    for seg in data.get("transcription", []):
        text = seg.get("text", "").strip()
        if not text or text.startswith("["):  # skip [BLANK_AUDIO], [Music] ...
            continue
        o = seg["offsets"]
        words.append(Word(o["from"] / 1000, o["to"] / 1000, text))
    return words


def sentences(words: list[Word], gap: float = 0.6) -> list[list[Word]]:
    """Group words into sentences on end punctuation or pauses."""
    out: list[list[Word]] = []
    cur: list[Word] = []
    for w in words:
        if cur and (w.start - cur[-1].end > gap):
            out.append(cur)
            cur = []
        cur.append(w)
        if w.text.rstrip()[-1:] in ".!?।":
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out
