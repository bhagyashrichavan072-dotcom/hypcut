"""HypeCut: clip the moments where stream chat (or the video itself) explodes."""
import os
import subprocess

__version__ = "0.1.0"

# Windows: when HypeCut runs from the desktop app there is no console, so every helper it starts
# (ffmpeg, ffprobe, whisper, yt-dlp, streamlink, powershell) would pop up its own black window.
# Start them all hidden instead. In a normal terminal nothing changes.
if os.name == "nt":
    try:
        import ctypes

        _no_console = ctypes.windll.kernel32.GetConsoleWindow() == 0
    except Exception:  # noqa: BLE001
        _no_console = True
    if _no_console and not getattr(subprocess.Popen, "_hypecut_hidden", False):
        _orig_init = subprocess.Popen.__init__

        def _hidden_init(self, *args, **kwargs):
            kwargs["creationflags"] = (kwargs.get("creationflags") or 0) | subprocess.CREATE_NO_WINDOW
            si = kwargs.get("startupinfo") or subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            kwargs["startupinfo"] = si
            _orig_init(self, *args, **kwargs)

        subprocess.Popen.__init__ = _hidden_init
        subprocess.Popen._hypecut_hidden = True
