"""Pick the best 15-30 s cut inside a spike window.

Score = chat hype inside the cut (shifted back by the reaction delay)
      + speech energy (loudness)
      + speech coverage (how much of the cut has words)
Cut edges snap to sentence starts/ends or silences, so nobody gets cut off mid-word.
"""
from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .transcribe import Word, sentences


@dataclass
class Cut:
    start: float   # relative to window start
    end: float
    score: float
    words: list[Word]


def loudness(wav: Path) -> np.ndarray:
    """RMS loudness per 0.5 s, normalised 0..1."""
    with wave.open(str(wav)) as w:
        sr = w.getframerate()
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    hop = sr // 2
    n = max(len(a) // hop, 1)
    rms = np.array([np.sqrt(np.mean(a[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(n)])
    return rms / max(rms.max(), 1e-6)


def best_cut(words: list[Word], wav: Path, window_len: float, chat_curve: np.ndarray,
             event_t: float, min_len: float, max_len: float) -> Cut:
    """chat_curve: weighted chat per second over the window (index 0 = window start), already delay-shifted.
    event_t: when the moment most likely happened (seconds from window start)."""
    loud = loudness(wav)
    sents = sentences(words)
    starts = {0.0} | {round(s[0].start - 0.15, 2) for s in sents}
    ends = {round(window_len, 2)} | {round(s[-1].end + 0.25, 2) for s in sents}
    # silences longer than 0.5 s are also good cut points
    for a, b in zip(words, words[1:]):
        if b.start - a.end > 0.5:
            mid = (a.end + b.start) / 2
            starts.add(round(mid, 2))
            ends.add(round(mid, 2))
    starts = sorted(x for x in starts if 0 <= x < window_len)
    ends = sorted(x for x in ends if 0 < x <= window_len)

    min_len = min(min_len, window_len)
    best: Cut | None = None
    for st in starts:
        for en in ends:
            L = en - st
            if L < min_len or L > max_len or not (st <= event_t <= en):
                continue
            i0, i1 = int(st), max(int(np.ceil(en)), int(st) + 1)
            chat = chat_curve[i0:i1].sum() / max(chat_curve.sum(), 1e-6)
            lo = loud[int(st * 2):int(en * 2)]
            energy = float(lo.mean()) if len(lo) else 0.0
            spoken = sum(min(w.end, en) - max(w.start, st) for w in words if w.end > st and w.start < en)
            coverage = spoken / L
            score = 0.5 * chat + 0.3 * energy + 0.2 * coverage + 0.02 * (L / max_len)  # tiny bias to fuller clips
            if best is None or score > best.score:
                best = Cut(st, en, score, [])
    if best is None:  # no snap points fit: centre a max_len cut on the event
        L = min(max_len, window_len)
        st = min(max(event_t - L * 0.66, 0.0), window_len - L)
        best = Cut(st, st + L, 0.0, [])
    best.words = [w for w in words if w.start >= best.start - 0.05 and w.end <= best.end + 0.05]
    return best
