"""Plans, trial, usage limits, sign-up and banner, all controlled remotely.

Every HypeCut copy reads `control.json` from the official GitHub repo (cached for an hour), so the
owner can switch limits, sign-up, the trial and the banner on or off for every user by editing
one file. Nothing here needs a server: the control file is hosted by GitHub, and sign-ups go to
a Google Form (responses land in a Google Sheet).

Plans:  trial (first N days after sign-up) -> free -> pro (license key, added at launch).
The owner's own copy sets "owner_mode": true in ~/.hypecut/config.json: no limits, no banner.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

HOME = Path.home() / ".hypecut"
ACCOUNT = HOME / "account.json"
USAGE = HOME / "usage.json"
CACHE = HOME / "control_cache.json"
CONFIG = HOME / "config.json"

# Set this to the raw URL of control.json once the GitHub repo exists.
CONTROL_URL = os.environ.get("HYPECUT_CONTROL_URL",
                             "https://raw.githubusercontent.com/OWNER/hypecut/main/control.json")

DEFAULT = {
    "version": 1, "enforce_limits": False, "require_signup": False, "trial_days": 14,
    "trial_line": "Trial version · {days} days left",
    "credits": {"per_clip": 5},
    "show_credits": False, "show_credits_from": "2026-11-23", "show_trial_from": "2026-11-23",
    "plans": {
        "trial": {"label": "Pro trial", "daily_credits": 250, "runs_per_day": None},
        "free": {"label": "Free", "daily_credits": 75, "runs_per_day": 5},
        "pro": {"label": "Pro", "daily_credits": 250, "runs_per_day": None},
    },
    "banner": {"show": False, "text": "", "button": "", "url": ""},
    "signup": {"form_url": "", "fields": {"name": "", "email": "", "instagram": ""}},
    "buy_url": "",
    "limit_message": "You've used today's clipping runs.",
}


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def _write(path: Path, data) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def developer() -> bool:
    """The owner's laptop copy (Developer tab). GitHub copies never have this flag."""
    return bool(_read(CONFIG, {}).get("owner_mode"))


def owner_mode() -> bool:
    """Owner perks (no limits, no trial line) - switched off while previewing the user version."""
    cfg = _read(CONFIG, {})
    return bool(cfg.get("owner_mode")) and not cfg.get("preview_user")


def remote() -> dict:
    """control.json from GitHub, cached for an hour; falls back to the cache, then DEFAULT."""
    cache = _read(CACHE, {})
    if cache.get("_fetched", 0) > time.time() - 3600 and cache.get("data"):
        return {**DEFAULT, **cache["data"]}
    if "OWNER/" not in CONTROL_URL:
        try:
            with urllib.request.urlopen(CONTROL_URL, timeout=6) as r:
                data = json.loads(r.read())
            _write(CACHE, {"_fetched": time.time(), "data": data})
            return {**DEFAULT, **data}
        except Exception:  # noqa: BLE001 - offline is fine
            pass
    return {**DEFAULT, **(cache.get("data") or {})}


# ---------------------------------------------------------------- account / plan
def account() -> dict:
    return _read(ACCOUNT, {})


def plan() -> tuple[str, int | None]:
    """(plan id, trial days left)."""
    if owner_mode():
        return "owner", None
    acc = account()
    if acc.get("plan") == "pro" and acc.get("pro_until", 0) > time.time():
        return "pro", None
    ctl = remote()
    start = acc.get("trial_started")
    if not start:  # trial starts on first use
        acc["trial_started"] = start = time.time()
        _write(ACCOUNT, acc)
    try:  # the trial clock starts no earlier than the launch date
        launch = dt.datetime.fromisoformat(str(ctl.get("show_trial_from") or "")).timestamp()
        start = max(start, launch)
    except ValueError:
        pass
    left = ctl["trial_days"] - int(max(time.time() - start, 0) // 86400)
    if left > 0:
        return "trial", left
    return "free", 0


def signup(name: str, email: str, instagram: str = "") -> dict:
    """Save the user's details locally and send them to the owner's Google Form (if configured)."""
    acc = account()
    acc.update({"name": name.strip(), "email": email.strip(), "instagram": instagram.strip(),
                "signed_up": time.time()})
    acc.setdefault("trial_started", time.time())
    sent = False
    form = remote().get("signup") or {}
    url, fields = form.get("form_url", ""), form.get("fields") or {}
    if url and fields.get("email"):
        data = {fields[k]: acc[k] for k in ("name", "email", "instagram") if fields.get(k)}
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                         headers={"Content-Type": "application/x-www-form-urlencoded"})
            urllib.request.urlopen(req, timeout=8).read()
            sent = True
        except Exception:  # noqa: BLE001
            pass
    acc["sent"] = sent or acc.get("sent", False)
    _write(ACCOUNT, acc)
    return acc


# ---------------------------------------------------------------- credits + usage limits
def _today() -> str:
    return dt.date.today().isoformat()


def _bucket(kind: str) -> str | None:
    return {"channel": "live", "video": "video", "file": "video"}.get(kind)  # demo is always free


def clip_cost(kind: str) -> int:
    b = _bucket(kind)
    if b is None:
        return 0
    return int((remote().get("credits") or {}).get("per_clip", 5))  # same price for every clip


def usage() -> dict:
    u = _read(USAGE, {})
    day = u.get(_today(), {})
    return {"runs": day.get("runs", 0), "credits_used": day.get("credits", 0), "clips": day.get("clips", 0),
            "total_runs": u.get("total", 0)}


def credits_left() -> int | None:
    """None = unlimited (owner)."""
    if owner_mode():
        return None
    p, _ = plan()
    daily = int(remote()["plans"].get(p, {}).get("daily_credits", 0))
    return max(daily - usage()["credits_used"], 0)


def check(kind: str, want_clips: int) -> tuple[bool, str, int]:
    """Can the user start this run? Returns (ok, message, max clips allowed)."""
    b = _bucket(kind)
    if b is None or owner_mode():
        return True, "", want_clips
    ctl = remote()
    if not ctl.get("enforce_limits"):
        return True, "", want_clips
    if ctl.get("require_signup") and not account().get("email"):
        return False, "Sign up first (it's free).", 0
    p, _ = plan()
    rules = ctl["plans"].get(p, {})
    u = usage()
    if rules.get("runs_per_day") is not None and u["runs"] >= rules["runs_per_day"]:
        return False, ctl.get("limit_message", "Daily limit reached."), 0
    left, cost = credits_left() or 0, clip_cost(kind)
    affordable = left // cost if cost else want_clips
    if affordable < 1:
        return False, ctl.get("limit_message", "No credits left today."), 0
    return True, "", min(want_clips, affordable)


def record_run(kind: str) -> None:
    if _bucket(kind) is None:
        return
    u = _read(USAGE, {})
    day = u.setdefault(_today(), {})
    day["runs"] = day.get("runs", 0) + 1
    u["total"] = u.get("total", 0) + 1
    _write(USAGE, u)


def spend(kind: str, clips: int) -> None:
    """Charge credits for finished clips (shown always; only blocks when limits are enforced)."""
    cost = clip_cost(kind)
    if not cost or clips <= 0:
        return
    u = _read(USAGE, {})
    day = u.setdefault(_today(), {})
    day["credits"] = day.get("credits", 0) + cost * clips
    day["clips"] = day.get("clips", 0) + clips
    _write(USAGE, u)


def status() -> dict:
    ctl = remote()
    p, left = plan()
    rules = ctl["plans"].get(p, {})
    u = usage()
    acc = account()
    cr = ctl.get("credits") or {}
    return {
        "plan": p, "label": "Owner" if p == "owner" else rules.get("label", p.title()), "trial_days_left": left,
        "developer": developer(), "preview_user": bool(_read(CONFIG, {}).get("preview_user")),
        "enforced": bool(ctl.get("enforce_limits")) and p != "owner",
        "daily_credits": None if p == "owner" else int(rules.get("daily_credits", 0)),
        "credits_left": credits_left(), "usage": u, "runs_per_day": rules.get("runs_per_day"),
        "cost_per_clip": int(cr.get("per_clip", 5)),
        "show_credits": bool(ctl.get("show_credits")) or (bool(ctl.get("show_credits_from"))
                                                          and _today() >= str(ctl.get("show_credits_from"))),
        "need_signup": bool(ctl.get("require_signup")) and not acc.get("email") and p != "owner",
        "signed_up": bool(acc.get("email")), "name": acc.get("name", ""),
        "banner": (ctl.get("banner") if (ctl.get("banner") or {}).get("show") and p != "owner" else None),
        "buy_url": ctl.get("buy_url", ""),
        "trial_line": (ctl.get("trial_line", "").replace("{days}", str(left))
                       if p == "trial" and ctl.get("trial_line")
                       and _today() >= str(ctl.get("show_trial_from") or "") else ""),
    }
