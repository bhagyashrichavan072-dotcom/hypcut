"""Live alerts: watch YouTube / Twitch channels and tell the user the moment they go live.

The desktop app runs `Watcher` in the background (while the app is open, minimized is fine).
Every few minutes it asks yt-dlp whether each channel is live. When a channel goes from offline to
live it shows a Windows notification + an in-app alert and, if the user switched it on, starts
clipping the live stream automatically.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

HOME = Path.home() / ".hypecut"
WATCH = HOME / "watch.json"


# ---------------------------------------------------------------- storage
def load() -> dict:
    try:
        d = json.loads(WATCH.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        d = {}
    d.setdefault("channels", [])
    d.setdefault("interval_min", 3)
    d.setdefault("alerts", [])
    return d


def save(d: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    WATCH.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize(url: str) -> tuple[str, str]:
    """(check URL, short name). Accepts @handle, youtube.com/@handle, /channel/ID, twitch.tv/name."""
    u = url.strip().strip('"')
    if re.fullmatch(r"@[\w.\-]+", u):
        u = "https://www.youtube.com/" + u
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    u = u.split("?")[0].rstrip("/")
    if "youtube.com" in u or "youtu.be" in u:
        m = re.search(r"youtube\.com/(@[\w.\-]+|channel/[\w\-]+|c/[\w.\-]+|user/[\w.\-]+)", u)
        if m:
            base = "https://www.youtube.com/" + m.group(1)
            return base + "/live", m.group(1).split("/")[-1]
        return u, u.rsplit("/", 1)[-1]
    m = re.search(r"twitch\.tv/([A-Za-z0-9_]+)", u)
    if m:
        return "https://www.twitch.tv/" + m.group(1).lower(), m.group(1)
    return u, u.rsplit("/", 1)[-1]


def add(url: str, auto_clip: bool = False) -> dict:
    d = load()
    check, name = normalize(url)
    if not any(c["url"] == check for c in d["channels"]):
        d["channels"].append({"url": check, "name": name, "auto_clip": auto_clip, "live": False,
                              "title": "", "live_url": "", "checked": 0, "error": ""})
    save(d)
    return d


def remove(url: str) -> dict:
    d = load()
    d["channels"] = [c for c in d["channels"] if c["url"] != url]
    save(d)
    return d


def set_auto(url: str, on: bool) -> dict:
    d = load()
    for c in d["channels"]:
        if c["url"] == url:
            c["auto_clip"] = bool(on)
    save(d)
    return d


# ---------------------------------------------------------------- live check
def _ytdlp() -> list[str]:
    import shutil

    return ["yt-dlp"] if shutil.which("yt-dlp") else [sys.executable, "-m", "yt_dlp"]


def is_live(url: str) -> tuple[bool, dict]:
    """Ask yt-dlp. Offline channels make it error with 'not currently live' / 'offline'."""
    try:
        r = subprocess.run(_ytdlp() + ["-J", "--no-warnings", "--skip-download", "--playlist-items", "1", url],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except subprocess.TimeoutExpired:
        return False, {"error": "check timed out"}
    if r.returncode != 0 or not r.stdout.strip():
        err = (r.stderr or "").lower()
        quiet = any(k in err for k in ("not currently live", "offline", "will begin", "premieres", "no video"))
        return False, {"error": "" if quiet else (r.stderr.strip().splitlines() or ["check failed"])[-1][:160]}
    info = json.loads(r.stdout)
    if info.get("_type") == "playlist":
        entries = [e for e in info.get("entries") or [] if e]
        info = entries[0] if entries else {}
    live = bool(info.get("is_live")) or info.get("live_status") == "is_live"
    return live, {"title": info.get("title") or "", "live_url": info.get("webpage_url") or url,
                  "name": info.get("uploader") or info.get("channel") or ""}


def notify(title: str, body: str) -> None:
    """Windows toast notification (no extra installs). Silent no-op elsewhere if it fails."""
    try:
        if os.name == "nt":
            t = title.replace("'", "''")
            b = body.replace("'", "''")
            ps = (
                "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
                "$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                f"$x.GetElementsByTagName('text')[0].AppendChild($x.CreateTextNode('{t}')) > $null;"
                f"$x.GetElementsByTagName('text')[1].AppendChild($x.CreateTextNode('{b}')) > $null;"
                "$n = [Windows.UI.Notifications.ToastNotification]::new($x);"
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
                "'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe').Show($n)"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=20)
        elif sys.platform == "darwin":
            subprocess.run(["osascript", "-e", f'display notification "{body}" with title "{title}"'], timeout=10)
        else:
            subprocess.run(["notify-send", title, body], timeout=10)
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------- background watcher
class Watcher:
    def __init__(self, on_live=None):
        self.on_live = on_live  # callback(channel) -> used to auto-start clipping
        self.lock = threading.Lock()
        self._wake = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    def check_now(self):
        self._wake.set()

    def check_all(self):
        with self.lock:
            d = load()
            results = {}
            for c in d["channels"]:
                was = c.get("live", False)
                live, info = is_live(c["url"])
                c["checked"] = time.time()
                c["error"] = info.get("error", "")
                c["live"] = live
                if live:
                    c["title"] = info.get("title", "")
                    c["live_url"] = info.get("live_url", c["url"])
                    if info.get("name"):
                        c["name"] = info["name"]
                results[c["url"]] = c
                if live and not was:
                    alert = {"t": time.time(), "name": c["name"], "title": c["title"], "url": c["live_url"],
                             "channel": c["url"], "seen": False}
                    d["alerts"] = ([alert] + d["alerts"])[:30]
                    notify(f"🔴 {c['name']} is LIVE", c["title"] or "Open HypeCut to clip it")
                    if c.get("auto_clip") and self.on_live:
                        try:
                            self.on_live(c)
                        except Exception as e:  # noqa: BLE001
                            c["error"] = f"auto-clip failed: {e}"
            # merge into the latest file, so channels added/removed during the check are kept
            latest = load()
            for c in latest["channels"]:
                if c["url"] in results:
                    keep_auto = c.get("auto_clip")
                    c.update(results[c["url"]])
                    c["auto_clip"] = keep_auto
            new_alerts = [a for a in d["alerts"] if a not in latest["alerts"]]
            latest["alerts"] = (new_alerts + latest["alerts"])[:30]
            save(latest)

    def _loop(self):
        time.sleep(5)
        while True:
            try:
                if load()["channels"]:
                    self.check_all()
            except Exception:  # noqa: BLE001 - the watcher must never die
                pass
            self._wake.wait(timeout=max(load()["interval_min"], 1) * 60)
            self._wake.clear()
