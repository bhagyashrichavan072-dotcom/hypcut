"""Build a 3-minute fake "stream" + matching chat log so anyone can try the clipper offline.

Video: ffmpeg test pattern (no real game footage). Voice: your OS text-to-speech
(Windows SAPI, macOS `say`, Linux espeak); if none is found the demo is silent and clips still render.
"""
from __future__ import annotations

import json
import platform
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

DURATION = 180
# (start second, what the "streamer" says)
LINES = [
    (5, "Okay chat, we are finally in Vice City. Let's just drive around and see what this game can do."),
    (30, "Wait, wait, wait. Is that a gator in the pool? Bro, the gator is chasing the cop! No way. "
         "The cop is running and the gator just jumped on the police car. Chat, clip that right now!"),
    (70, "Alright, let me check the map. I think the next mission is somewhere up north."),
    (98, "Okay, heist time. Lucia goes in first, I take the car. Oh no, five stars. Five stars already! "
         "Helicopter, helicopter! I am jumping off the bridge. Let's go, we made it! We actually made it!"),
    (145, "Let me try the parachute. Wait, why am I flying? The ragdoll physics are insane. "
          "I just bounced off a palm tree into the ocean. Wasted. Wasted again, chat."),
]
PEAKS = [46, 116, 163]  # where chat explodes (a few seconds after the moment)

FILLER = ["hi chat", "first time here", "what graphics settings?", "vice city looks clean", "lol", "nice car",
          "is this on pc?", "hello from india", "bhai mast", "how long is the map", "music is fire", "ok",
          "drive to the beach", "jason or lucia?", "the reflections tho", "60fps?", "W stream", "hey everyone"]
HYPE = {
    46: ["KEKW", "GATOR KEKW", "CLIP IT", "clip that", "NO WAY 😂", "OMEGALUL", "the gator 💀", "LMAO",
         "gator > cops", "W GATOR", "clip it clip it", "LUL", "bro got eaten", "WWWW", "florida man energy KEKW"],
    116: ["5 STARS", "LETS GOOO", "POGGERS", "W HEIST", "omg the bridge", "Pog", "five stars already lmao",
          "HE MADE IT", "WWW", "insane", "clip it", "monkaS heli", "🔥🔥🔥", "no way he made that", "PogChamp"],
    163: ["WASTED", "ragdoll 💀", "LMAO", "KEKW", "wasted again lol", "OMEGALUL", "the palm tree 😂",
          "physics are crazy", "clip that", "L parachute", "LUL", "bro flew", "😂😂", "WASTED KEKW", "ragdoll king"],
}


def make_chat(path: Path, seed: int = 6) -> Path:
    rnd = random.Random(seed)
    users = [f"viewer{n:03d}" for n in range(1, 400)]
    msgs = []
    for sec in range(DURATION):
        rate = 1.2
        for p in PEAKS:
            d = sec - p
            if -4 <= d <= 8:
                rate += 11 * (2.718 ** (-(d ** 2) / 10))
        for _ in range(_poisson(rnd, rate)):
            hot = [p for p in PEAKS if -3 <= sec - p <= 7]
            text = rnd.choice(HYPE[hot[0]]) if hot and rnd.random() < 0.8 else rnd.choice(FILLER)
            msgs.append({"t": round(sec + rnd.random(), 2), "user": rnd.choice(users), "text": text})
    msgs.sort(key=lambda m: m["t"])
    path.write_text("".join(json.dumps(m, ensure_ascii=False) + "\n" for m in msgs), encoding="utf-8")
    return path


def _poisson(rnd: random.Random, lam: float) -> int:
    L, k, p = 2.718281828 ** -lam, 0, 1.0
    while True:
        p *= rnd.random()
        if p < L:
            return k
        k += 1


def _tts(text: str, out: Path) -> bool:
    system = platform.system()
    try:
        if system == "Windows":
            ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                  f"$s.Rate = 1; $s.SetOutputToWaveFile('{out}'); $s.Speak('{text.replace(chr(39), '')}'); $s.Dispose()")
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True)
        elif system == "Darwin":
            aiff = out.with_suffix(".aiff")
            subprocess.run(["say", "-o", str(aiff), text], check=True)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), str(out)], check=True)
        else:
            exe = shutil.which("espeak-ng") or shutil.which("espeak")
            if not exe:
                return False
            subprocess.run([exe, "-w", str(out), text], check=True)
        return out.exists() and out.stat().st_size > 1000
    except (OSError, subprocess.CalledProcessError):
        return False


def make_video(path: Path) -> Path:
    with tempfile.TemporaryDirectory() as td:
        voice = []
        for i, (start, text) in enumerate(LINES):
            w = Path(td) / f"line{i}.wav"
            if _tts(text, w):
                voice.append((start, w))
        if not voice:
            print("[demo] no text-to-speech found: demo will be silent (captions will be empty)")
        cmd = ["ffmpeg", "-y", "-loglevel", "error",
               "-f", "lavfi", "-i", f"testsrc2=s=1280x720:r=30:d={DURATION}",
               "-f", "lavfi", "-i", f"anoisesrc=color=brown:amplitude=0.015:d={DURATION}"]
        for _, w in voice:
            cmd += ["-i", str(w)]
        mix = "".join(f"[{k + 2}:a]aresample=48000,adelay={int(st * 1000)}:all=1[v{k}];" for k, (st, _) in enumerate(voice))
        mix += "[1:a]" + "".join(f"[v{k}]" for k in range(len(voice)))
        mix += f"amix=inputs={len(voice) + 1}:normalize=0:duration=first[a]"
        vf = "[0:v]drawtext=text='DEMO STREAM  %{pts\\:hms}':x=40:y=40:fontsize=42:fontcolor=white:box=1:boxcolor=black@0.6[v]"
        base = cmd + ["-filter_complex", mix + ";" + vf, "-map", "[v]", "-map", "[a]",
                      "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-c:a", "aac", "-shortest", str(path)]
        r = subprocess.run(base, capture_output=True, text=True)
        if r.returncode != 0:  # drawtext needs a font; retry without the label
            base = cmd + ["-filter_complex", mix + ";[0:v]null[v]", "-map", "[v]", "-map", "[a]",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-c:a", "aac", "-shortest", str(path)]
            subprocess.run(base, check=True)
    return path


def make_demo(folder: Path) -> tuple[Path, Path]:
    folder.mkdir(parents=True, exist_ok=True)
    chat = folder / "demo_chat.jsonl"
    video = folder / "demo_stream.mp4"
    if not chat.exists():
        make_chat(chat)
    if not video.exists():
        print("[demo] building a 3-minute demo stream (test pattern + text-to-speech) ...")
        make_video(video)
    return video, chat


if __name__ == "__main__":
    v, c = make_demo(Path("samples"))
    print(v, c)
