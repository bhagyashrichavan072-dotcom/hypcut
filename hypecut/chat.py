"""Chat sources: local chat logs, VOD chat replay, and live Twitch IRC / YouTube chat.

Everything is normalised to ChatMessage(t, user, text) where t = seconds from stream start.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class ChatMessage:
    t: float
    user: str
    text: str


# ---------------------------------------------------------------- file loaders
_TXT_LINE = re.compile(r"^\[?(?P<ts>\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\]?\s+(?P<user>[^:]+?):\s?(?P<text>.*)$")


def _hms(ts: str) -> float:
    parts = [float(p) for p in ts.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def load_chat_file(path: str | Path) -> list[ChatMessage]:
    """Load .jsonl (ours), yt-dlp live_chat.json, .csv (t,user,text) or .txt ('[00:01:23] user: msg')."""
    path = Path(path)
    msgs: list[ChatMessage] = []
    suffix = path.suffix.lower()
    with open(path, encoding="utf-8", errors="replace") as f:
        if suffix == ".csv":
            for row in csv.DictReader(f):
                t = row.get("t") or row.get("time") or row.get("seconds") or "0"
                msgs.append(ChatMessage(_hms(t) if ":" in t else float(t), row.get("user", "?"), row.get("text", "")))
        elif suffix in (".jsonl", ".json"):
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                m = _from_json_obj(obj)
                if m:
                    msgs.append(m)
        else:
            for line in f:
                mt = _TXT_LINE.match(line.strip())
                if mt:
                    msgs.append(ChatMessage(_hms(mt["ts"]), mt["user"].strip(), mt["text"]))
    msgs.sort(key=lambda m: m.t)
    return msgs


def _from_json_obj(obj: dict) -> ChatMessage | None:
    if "t" in obj and "text" in obj:  # our own format
        return ChatMessage(float(obj["t"]), obj.get("user", "?"), obj["text"])
    if "time_in_seconds" in obj:      # chat-downloader output
        return ChatMessage(float(obj["time_in_seconds"]), (obj.get("author") or {}).get("name", "?"), obj.get("message") or "")
    # yt-dlp YouTube live_chat.json (one replay action per line)
    act = obj.get("replayChatItemAction")
    if act:
        offset = float(act.get("videoOffsetTimeMsec", 0)) / 1000
        for a in act.get("actions", []):
            item = (a.get("addChatItemAction") or {}).get("item", {})
            r = item.get("liveChatTextMessageRenderer") or item.get("liveChatPaidMessageRenderer")
            if not r:
                continue
            runs = (r.get("message") or {}).get("runs", [])
            text = "".join(x.get("text") or (x.get("emoji", {}).get("shortcuts") or [""])[0] for x in runs)
            user = (r.get("authorName") or {}).get("simpleText", "?")
            return ChatMessage(offset, user, text)
    return None


def save_chat_jsonl(msgs: list[ChatMessage], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for m in msgs:
            f.write(json.dumps(asdict(m), ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- VOD replay
def fetch_vod_chat(url: str, out_dir: Path) -> list[ChatMessage]:
    """Twitch VOD / YouTube VOD chat replay. Tries chat-downloader, then yt-dlp (YouTube only)."""
    try:
        from chat_downloader import ChatDownloader  # type: ignore

        print("[chat] downloading chat replay with chat-downloader ...")
        msgs = [
            ChatMessage(float(m.get("time_in_seconds", 0)), (m.get("author") or {}).get("name", "?"), m.get("message") or "")
            for m in ChatDownloader().get_chat(url)
            if m.get("time_in_seconds") is not None
        ]
        if msgs:
            return msgs
    except ImportError:
        pass
    except Exception as e:  # noqa: BLE001
        print(f"[chat] chat-downloader failed: {e}")

    if shutil.which("yt-dlp") is None and not _has_module("yt_dlp"):
        raise SystemExit("Need `pip install chat-downloader` (Twitch+YouTube) or yt-dlp (YouTube) to read VOD chat.")
    print("[chat] downloading live_chat replay with yt-dlp ...")
    base = out_dir / "vod_chat"
    subprocess.run(_ytdlp() + ["--skip-download", "--write-subs", "--sub-langs", "live_chat", "-o", str(base), url], check=False)
    found = list(out_dir.glob("vod_chat*.live_chat.json"))
    if not found:
        raise SystemExit("Could not get chat replay. For Twitch VODs install chat-downloader: pip install chat-downloader")
    return load_chat_file(found[0])


def _has_module(name: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(name) is not None


def _ytdlp() -> list[str]:
    import sys

    return ["yt-dlp"] if shutil.which("yt-dlp") else [sys.executable, "-m", "yt_dlp"]


# ---------------------------------------------------------------- live chat
class LiveChat:
    """Collects live chat in a background thread. t is seconds since `t0` (shared with the video buffer)."""

    def __init__(self, url: str, t0: float):
        self.url, self.t0 = url, t0
        self.messages: list[ChatMessage] = []
        self.lock = threading.Lock()
        self._stop = threading.Event()
        target = self._twitch if "twitch.tv" in url else self._youtube
        self.thread = threading.Thread(target=target, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self._stop.set()

    def snapshot(self) -> list[ChatMessage]:
        with self.lock:
            return list(self.messages)

    def _add(self, user: str, text: str):
        with self.lock:
            self.messages.append(ChatMessage(time.time() - self.t0, user, text))

    def _twitch(self):
        """Anonymous read-only Twitch IRC (no account/token needed)."""
        channel = re.search(r"twitch\.tv/([A-Za-z0-9_]+)", self.url).group(1).lower()
        while not self._stop.is_set():
            try:
                s = socket.create_connection(("irc.chat.twitch.tv", 6667), timeout=30)
                s.sendall(b"NICK justinfan%d\r\n" % (int(time.time()) % 100000))
                s.sendall(f"JOIN #{channel}\r\n".encode())
                print(f"[chat] connected to twitch chat #{channel}")
                buf = b""
                while not self._stop.is_set():
                    data = s.recv(4096)
                    if not data:
                        break
                    buf += data
                    *lines, buf = buf.split(b"\r\n")
                    for raw in lines:
                        line = raw.decode("utf-8", "replace")
                        if line.startswith("PING"):
                            s.sendall(b"PONG :tmi.twitch.tv\r\n")
                            continue
                        m = re.match(r"^:(\w+)!\S+ PRIVMSG #\w+ :(.*)$", line)
                        if m:
                            self._add(m.group(1), m.group(2))
            except OSError as e:
                print(f"[chat] twitch chat dropped ({e}); reconnecting in 3s")
                time.sleep(3)

    def _youtube(self):
        try:
            from chat_downloader import ChatDownloader  # type: ignore
        except ImportError:
            print("[chat] YouTube live chat needs: pip install chat-downloader")
            return
        for m in ChatDownloader().get_chat(self.url):
            if self._stop.is_set():
                break
            self._add((m.get("author") or {}).get("name", "?"), m.get("message") or "")
