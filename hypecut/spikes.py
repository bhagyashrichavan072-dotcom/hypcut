"""Chat spike detection: weighted messages/sec vs a rolling baseline (z-score)."""
from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from .chat import ChatMessage
from .config import Settings

# Weight added on top of 1.0 per message. Lowercase keys; matched as whole words/phrases.
HYPE_WORDS: dict[str, float] = {
    # "clip it" is the strongest signal there is
    "clip it": 4, "clip that": 4, "clipped": 3, "clip": 3,
    # twitch / 7tv emotes
    "kekw": 2, "omegalul": 2.5, "lul": 1.5, "lulw": 1.5, "pog": 2, "pogchamp": 2, "poggers": 2,
    "pogu": 2, "monkas": 1.5, "pepelaugh": 2, "w": 1.5, "ww": 1.5, "www": 2, "l": 1, "ez": 1,
    "kappa": 0.5, "sadge": 1, "aware": 1, "o7": 1,
    # reactions
    "omg": 1.5, "lmao": 1.5, "lmfao": 2, "lol": 1, "haha": 1, "hahaha": 1.5, "wtf": 1.5, "no way": 2,
    "bro": 0.5, "insane": 2, "crazy": 1.5, "holy": 1.5, "nahh": 1.5, "????": 1.5, "!!!": 1,
    # GTA 6 specific
    "wasted": 2, "busted": 2, "5 stars": 2, "five stars": 2, "wanted": 1, "heist": 1.5, "chase": 1.5,
    "cops": 1, "police": 1, "jason": 1, "lucia": 1, "vice city": 1.5, "leonida": 1, "gator": 1.5,
    "crash": 1, "ragdoll": 1.5, "glitch": 1.5, "bug": 1,
    # hinglish
    "bhai": 0.5, "op": 1.5, "mast": 1, "kya": 0.5, "pagal": 1.5, "gajab": 1.5,
}
EMOJI_WEIGHTS = {"😂": 1.5, "🤣": 1.5, "🔥": 1, "💀": 1.5, "😭": 1, "😱": 1.5, "🤯": 1.5, "‼": 1}


@dataclass
class Spike:
    peak: float     # seconds (chat time) where activity peaked
    z: float        # how unusual it was
    rate: float     # weighted messages/sec at the peak
    start: float    # clip window start (stream time)
    end: float      # clip window end
    top_messages: list[str]
    kind: str = "chat"   # chat | video (no-chat hype) | story (best moments of a talking video)


def message_weight(text: str, extra: dict[str, float] | None = None) -> float:
    words = HYPE_WORDS | (extra or {})
    low = " " + re.sub(r"\s+", " ", text.lower()) + " "
    bonus = 0.0
    for key, w in words.items():
        if re.search(r"(?<![\w])" + re.escape(key) + r"(?![\w])", low):
            bonus += w
    bonus += sum(w for e, w in EMOJI_WEIGHTS.items() if e in text)
    letters = [c for c in text if c.isalpha()]
    if len(letters) >= 4 and sum(c.isupper() for c in letters) / len(letters) > 0.7:
        bonus += 0.5  # ALL CAPS
    return 1.0 + min(bonus, 5.0)


def activity_curve(msgs: list[ChatMessage], s: Settings, duration: float | None = None):
    """Return (per-second weighted counts, smoothed rate per second)."""
    end = duration if duration else (msgs[-1].t + 1 if msgs else 1)
    n = max(int(np.ceil(end)) + 1, 1)
    counts = np.zeros(n)
    for m in msgs:
        i = int(m.t)
        if 0 <= i < n:
            counts[i] += message_weight(m.text, s.hype_words)
    k = max(int(s.smooth_seconds), 1)
    smooth = np.convolve(counts, np.ones(k) / k, mode="same")
    return counts, smooth


def zscores(smooth: np.ndarray, s: Settings) -> np.ndarray:
    b = int(s.baseline_seconds)
    z = np.zeros_like(smooth)
    for i in range(len(smooth)):
        lo = max(0, i - b)
        hist = smooth[lo:max(lo, i - int(s.smooth_seconds))]  # exclude the moment itself
        if len(hist) < 10:
            continue
        # robust baseline (median + MAD) so an earlier spike doesn't hide the next one
        mu = float(np.median(hist))
        sd = 1.4826 * float(np.median(np.abs(hist - mu)))
        z[i] = (smooth[i] - mu) / max(sd, 0.5)
    return z


def pick_peaks(smooth: np.ndarray, z: np.ndarray, s: Settings, duration: float | None,
               exclude: list[tuple[float, float]] | None = None, fill: bool = True,
               min_level: float | None = None, top_fn=None, kind: str = "chat") -> list[Spike]:
    """Shared by every clip mode: choose up to s.max_clips separate, non-overlapping moments.

    Strong peaks (z >= threshold and level >= min_level) first, strongest first; then, if fill,
    the next-best peaks so a long video always gives a full set. Windows overlapping `exclude`
    (moments clipped in earlier runs) are skipped.
    """
    min_level = s.min_rate if min_level is None else min_level
    gap = max(s.min_gap, s.pre_seconds + s.post_seconds)
    exclude = exclude or []

    def window(i: int) -> tuple[float, float]:
        a = max(0.0, i - s.pre_seconds)
        b = i + s.post_seconds
        return a, (min(b, duration) if duration else b)

    def free(i: int) -> bool:
        a, b = window(i)
        if b - a < s.min_clip:
            return False
        return all(b <= x or a >= y for x, y in exclude)

    peaks = [i for i in range(1, len(smooth) - 1)
             if smooth[i] > 0 and smooth[i] >= smooth[i - 1] and smooth[i] >= smooth[i + 1]]
    strong = sorted((i for i in peaks if z[i] >= s.z_threshold and smooth[i] >= min_level),
                    key=lambda i: z[i] * smooth[i], reverse=True)
    strong_set = set(strong)
    weak = sorted((i for i in peaks if i not in strong_set),
                  key=lambda i: (max(z[i], 0) + 1) * smooth[i], reverse=True) if fill else []

    chosen: list[int] = []
    for i in strong + weak:
        if len(chosen) >= s.max_clips:
            break
        if free(i) and all(abs(i - j) >= gap for j in chosen):
            chosen.append(i)

    out = []
    for i in sorted(chosen):
        a, b = window(i)
        out.append(Spike(float(i), float(z[i]), float(smooth[i]), a, b, top_fn(float(i)) if top_fn else [], kind))
    return out


def detect_spikes(msgs: list[ChatMessage], s: Settings, duration: float | None = None,
                  exclude: list[tuple[float, float]] | None = None, fill: bool = True) -> list[Spike]:
    """Chat mode: moments where chat explodes."""
    if not msgs:
        return []
    _, smooth = activity_curve(msgs, s, duration)
    z = zscores(smooth, s)

    def top(peak: float) -> list[str]:
        t = [m.text for m in msgs if peak - 3 <= m.t <= peak + 3]
        t.sort(key=lambda x: message_weight(x, s.hype_words), reverse=True)
        return t[:8]

    return pick_peaks(smooth, z, s, duration, exclude, fill, top_fn=top)
