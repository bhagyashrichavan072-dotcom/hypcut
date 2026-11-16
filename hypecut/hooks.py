"""Hooks and scores that work with no API key.

- offline_hook(): a short on-screen hook + title built from the transcript and what chat spammed.
- hook_score(): 0-100 heuristic for a hook line (short, concrete, stakes, payload up front).
  If you have an external scorer (e.g. a Claude Code `ig-reel` skill's hookscore.py), point
  HYPECUT_HOOKSCORE at it and it is used instead.
- viral_score(): 0-100 blend of how hard chat exploded, the cut quality and the hook.
Gemini (ai.py) overrides the offline hook/title when GEMINI_API_KEY is set.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter

# Things chat spams -> the hook they suggest
CHAT_THEMES = [
    (r"\bwasted\b", "WASTED in 3 seconds"),
    (r"5 stars|five stars", "5 stars in 10 seconds"),
    (r"gator|alligator", "The gator won this one"),
    (r"heist", "This heist should not have worked"),
    (r"ragdoll|physics|flew|flying", "GTA 6 physics are broken"),
    (r"bridge|jump", "He actually made that jump"),
    (r"cop|police", "The cops never saw it coming"),
    (r"glitch|bug", "GTA 6 glitch nobody expected"),
    (r"kekw|lmao|lul|omegalul|😂|💀", "Chat could not stop laughing"),
    (r"pog|w\b|www|lets go", "Chat went crazy for this"),
]
STAKE_WORDS = {"never", "nobody", "broke", "broken", "won", "lost", "wasted", "insane", "actually", "should",
                "not", "crazy", "only", "first", "last", "stop", "secret", "why", "how"}
WEAK_STARTS = ("hi", "hey", "hello", "so ", "okay", "ok ", "welcome", "in this video", "today")


def offline_hook(transcript: str, chat: list[str]) -> tuple[str, str]:
    """Return (hook, title). Hook = first on-screen line (max ~7 words). Title = file/post title."""
    if not chat:  # no chat: hook = the punchiest short line the speaker said
        sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", transcript) if 3 <= len(x.split()) <= 12]
        if sents:
            sents.sort(key=lambda x: (("!" in x) + ("?" in x) + sum(w.lower().strip(".,!?") in STAKE_WORDS
                                                                    for w in x.split())), reverse=True)
            hook = " ".join(sents[0].rstrip(".").split()[:7])
            title = next((x.rstrip(".") for x in sents[1:] if x != sents[0]), hook)
            return hook, title
        return "Wait for it", "Best moment"
    blob = (" ".join(chat) + " " + " ".join(chat) + " " + transcript).lower()  # chat counts double
    counts = Counter()
    for k, (pattern, hook) in enumerate(CHAT_THEMES):
        generic = k >= len(CHAT_THEMES) - 2  # "chat laughed / went crazy" only wins if nothing specific was said
        counts[hook] = len(re.findall(pattern, blob)) * (0.3 if generic else 1.0)
    theme, n = counts.most_common(1)[0] if counts else ("", 0)
    hook = theme if n else "Chat lost it at this moment"
    # title: the most quotable short sentence the streamer said
    sents = [x.strip() for x in re.split(r"(?<=[.!?])\s+", transcript) if 2 <= len(x.split()) <= 9]
    sents.sort(key=lambda x: (("!" in x) + sum(w.lower().strip(".,!?") in STAKE_WORDS for w in x.split())), reverse=True)
    title = sents[0].rstrip(".") if sents else hook
    return hook, title


def _builtin_hook_score(line: str) -> int:
    words = re.findall(r"[\w']+", line)
    n = len(words)
    length = 100 if 3 <= n <= 8 else max(0, 100 - 15 * abs(n - 6))
    concrete = 100 if re.search(r"\d|five|ten|three|gta|gator|cops?|heist|bridge|stars?", line, re.I) else 40
    stakes = min(100, 40 + 30 * sum(w.lower() in STAKE_WORDS for w in words))
    front = 30 if line.lower().startswith(WEAK_STARTS) else 100
    return round(0.3 * length + 0.25 * concrete + 0.25 * stakes + 0.2 * front)


def hook_score(line: str) -> int:
    ext = os.environ.get("HYPECUT_HOOKSCORE")
    if ext and os.path.exists(ext):
        try:
            r = subprocess.run([sys.executable, ext, "--hook", line, "--json"], capture_output=True, text=True, timeout=20)
            data = json.loads(r.stdout)
            item = data[0] if isinstance(data, list) else data
            for key in ("score", "total", "overall"):
                if key in item:
                    return int(round(float(item[key])))
        except Exception:  # noqa: BLE001
            pass
    return _builtin_hook_score(line)


def viral_score(z: float, cut_score: float, hook: int) -> int:
    chat = min(z / 10, 1.0) * 100          # z >= 10 is a monster spike
    cut = min(max(cut_score, 0) / 0.8, 1.0) * 100
    return round(0.55 * chat + 0.2 * cut + 0.25 * hook)
