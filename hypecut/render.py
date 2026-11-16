"""Render a 9:16 vertical clip: hook card, title bar, word-by-word captions, chat pop-ups, punch-zoom,
face tracking (auto) or blurred-background layout."""
from __future__ import annotations

import numpy as np

import random
import subprocess
from pathlib import Path

from .config import Settings
from .transcribe import Word

HOOK_SECONDS = 2.5
YELLOW = r"&H00E5FF&"


def _ass_time(t: float) -> str:
    t = max(t, 0)
    h, rem = divmod(t, 3600)
    m, sec = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{sec:05.2f}"


def _esc(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def write_ass(words: list[Word], path: Path, s: Settings, title: str | None = None, clip_len: float = 0,
              hook: str | None = None, chat: list[str] | None = None, event_t: float | None = None) -> Path:
    W, H = s.width, s.height
    fs = int(H * 0.042)
    upper = s.caption_style != "clean"
    border = 3 if s.caption_style == "box" else 1
    back = "&H0000E5FF" if s.caption_style == "box" else "&H64000000"  # ASS colours are &HAABBGGRR
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{s.caption_font},{fs},{"&H00000000" if s.caption_style == "box" else "&H00FFFFFF"},&H00FFFFFF,{back if s.caption_style == "box" else "&H00000000"},{back},-1,0,0,0,100,100,0,0,{border},{max(fs // 12, 3)},2,2,60,60,{int(H * 0.22)},1
Style: Title,{s.caption_font},{int(fs * 0.95)},&H00FFFFFF,&H00FFFFFF,&H00000000,&HB4000000,-1,0,0,0,100,100,0,0,3,18,0,8,70,70,{int(H * 0.07)},1
Style: Hook,{s.caption_font},{int(fs * 1.45)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,{fs // 7},4,5,80,80,0,1
Style: Chat,{s.caption_font},{int(fs * 0.55)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96301E1E,-1,0,0,0,100,100,0,0,3,14,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    hook_end = HOOK_SECONDS if (hook and s.hook_card) else 0.0
    if hook_end:
        # pops in (scale 70% -> 100%), sits in the upper third
        lines.append(f"Dialogue: 3,{_ass_time(0)},{_ass_time(hook_end)},Hook,,0,0,0,,"
                     rf"{{\pos({W // 2},{int(H * 0.30)})\fscx70\fscy70\t(0,180,\fscx100\fscy100)\fad(0,200)}}"
                     + _esc(hook.upper()))
    if title and s.title_overlay:
        # title sits at the top for the whole clip, first frame to last
        lines.append(f"Dialogue: 4,{_ass_time(0)},{_ass_time(clip_len)},Title,,0,0,0,,{_esc(title.upper())}")

    # chat messages flying in at the moment chat exploded
    if s.effects and chat and event_t is not None:
        rnd = random.Random(len(chat))
        for k, msg in enumerate(chat[:5]):
            t0 = event_t + 0.5 + k * 0.45
            if t0 >= clip_len:
                break
            y = int(H * (0.36 + 0.055 * k))
            x = 60 + rnd.randint(0, 120)
            lines.append(f"Dialogue: 2,{_ass_time(t0)},{_ass_time(min(t0 + 2.8, clip_len))},Chat,,0,0,0,,"
                         rf"{{\move({x - 260},{y},{x},{y},0,160)\fad(0,300)}}" + _esc(msg[:40]))

    n = max(s.words_per_caption, 1)
    groups = [words[i:i + n] for i in range(0, len(words), n)]
    for gi, g in enumerate(groups):
        for wi, w in enumerate(g):
            start = max(w.start, hook_end) if w.end > hook_end else None
            if start is None:
                continue  # hook card covers the first seconds
            if wi + 1 < len(g):
                end = g[wi + 1].start
            elif gi + 1 < len(groups):
                end = min(groups[gi + 1][0].start, w.end + 0.6)
            else:
                end = w.end + 0.6
            if end <= start:
                end = start + 0.1
            parts = []
            for wj, x in enumerate(g):
                t = _esc(x.text.upper() if upper else x.text)
                if wj == wi and s.caption_style != "box":
                    t = r"{\c" + YELLOW + r"}" + t + r"{\c&HFFFFFF&}"
                parts.append(t)
            text = " ".join(parts) if s.caption_style != "box" else _esc(w.text.upper())
            lines.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Cap,,0,0,0,,{text}")
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    return path


_ENCODER: list[str] | None = None


def encoder() -> list[str]:
    """Fastest H.264 encoder that works here: NVIDIA (nvenc), Intel (qsv), AMD (amf), else CPU x264."""
    global _ENCODER
    if _ENCODER is not None:
        return _ENCODER
    options = [
        ["-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "21", "-b:v", "0"],
        ["-c:v", "h264_qsv", "-preset", "faster", "-global_quality", "22"],
        ["-c:v", "h264_amf", "-quality", "speed", "-rc", "cqp", "-qp_i", "21", "-qp_p", "23"],
    ]
    for opt in options:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                            "color=c=black:s=720x1280:d=0.2", *opt, "-f", "null", "-"], capture_output=True)
        if r.returncode == 0:
            _ENCODER = opt
            print(f"[render] using GPU encoder {opt[1]}", flush=True)
            return _ENCODER
    _ENCODER = ["-c:v", "libx264", "-preset", "superfast", "-crf", "21", "-threads", "0"]
    return _ENCODER


def _probe_size(src: str) -> tuple[int, int]:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", src], capture_output=True, text=True)
    w, h = (int(x) for x in r.stdout.strip().split(",")[:2])
    return w, h


def face_track(src: str, start: float, dur: float) -> tuple[float, int, int] | None:
    """Where is the main face? Grabs 8 small frames in ONE ffmpeg pass (GPU decode), finds the face.
    Returns (centre x as 0..1, width, height) or None when there is no clear, big face."""
    try:
        import cv2  # type: ignore
        cv2.CascadeClassifier  # noqa: B018 - missing in OpenCV 5: then no face tracking, no crash
    except (ImportError, AttributeError):
        return None
    try:
        W, H = _probe_size(src)
    except Exception:  # noqa: BLE001
        return None
    if W <= H:  # already vertical
        return None
    n, sw = 8, 480
    sh = int(sw * H / W) // 2 * 2
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-hwaccel", "auto", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}",
                        "-i", src, "-vf", f"fps={n / max(dur, 1):.4f},scale={sw}:{sh}", "-frames:v", str(n),
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    frames = np.frombuffer(r.stdout, dtype=np.uint8)
    count = len(frames) // (sw * sh)
    if not count:
        return None
    det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    xs = []
    for k in range(count):
        gray = frames[k * sw * sh:(k + 1) * sw * sh].reshape(sh, sw)
        faces = det.detectMultiScale(gray, 1.15, 6, minSize=(30, 30))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            if w / sw >= 0.07:  # ignore tiny faces (e.g. a small facecam in a corner)
                xs.append((x + w / 2) / sw)
    if len(xs) < 0.5 * count:
        return None
    return float(np.median(xs)), W, H


def render_vertical(src: str, start: float, dur: float, out: Path, ass: Path | None, s: Settings,
                    event_t: float | None = None) -> Path:
    W, H = s.width, s.height
    face = face_track(src, start, dur) if s.layout in ("auto", "face") else None
    if face:
        cx, iw, ih = face
        cw = min(int(ih * 9 / 16) // 2 * 2, iw)
        x = int(min(max(cx * iw - cw / 2, 0), iw - cw))
        vf = f"[0:v]crop={cw}:{ih}:{x}:0,scale={W}:{H}"
        print(f"[render] face tracking: keeping the face centred (x={cx:.2f})")
    elif s.layout == "crop":
        vf = f"[0:v]scale=-2:{H},crop={W}:{H}"
    else:  # blurred fill: sharp 16:9 video in the middle, blurred copy behind it
        vf = (f"[0:v]split=2[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"boxblur=20:2,eq=brightness=-0.08[bg];[b]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    if s.effects and event_t is not None:
        # punch-zoom 115% for 1.2 s on the moment (hard cut in, hard cut out)
        a, b = max(event_t - 0.3, 0), event_t + 0.9
        zw, zh = int(W * 1.15) // 2 * 2, int(H * 1.15) // 2 * 2
        vf += (f",scale=w='if(between(t\\,{a:.2f}\\,{b:.2f})\\,{zw}\\,{W})':"
               f"h='if(between(t\\,{a:.2f}\\,{b:.2f})\\,{zh}\\,{H})':eval=frame,crop={W}:{H}")
    if ass is not None:
        # run ffmpeg inside the clip folder so the .ass path needs no Windows drive-letter escaping
        vf += ",ass=" + ass.name
    vf += "[v]"
    def cmd(enc: list[str], hw: bool) -> list[str]:
        return (["ffmpeg", "-y", "-loglevel", "error"] + (["-hwaccel", "auto"] if hw else [])
                + ["-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", str(Path(src).resolve()),
                   "-filter_complex", vf, "-map", "[v]", "-map", "0:a?", *enc,
                   "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out.name])

    r = subprocess.run(cmd(encoder(), True), cwd=str(out.parent), capture_output=True, text=True)
    if r.returncode != 0:  # GPU path failed on this file: plain CPU path
        subprocess.run(cmd(["-c:v", "libx264", "-preset", "superfast", "-crf", "21", "-threads", "0"], False),
                       check=True, cwd=str(out.parent))
    return out
