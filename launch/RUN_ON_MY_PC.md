# HypeCut on Kunal's PC (already installed)

HypeCut is installed (`pip install -e .` from this folder), so the `hypecut` command works in any terminal.
Code changes in this folder apply straight away; there's no need to reinstall.

## Every time you open PowerShell (uses your whisper.cpp, no model download)
```powershell
$env:HYPECUT_WHISPER_CPP="C:\Users\kunal mhetre\Desktop\kunal\Apps\Video Tools\whisper\Release\whisper-cli.exe"
$env:HYPECUT_WHISPER_MODEL="C:\Users\kunal mhetre\Desktop\kunal\Apps\Video Tools\models\ggml-base.bin"
$env:GEMINI_API_KEY="your-key"   # optional: better hooks/titles/captions
cd "C:\Users\kunal mhetre\Desktop\gta6-chat-clipper"
```
Skip the two whisper lines to use faster-whisper instead (it downloads about 150 MB the first time).

## Run it
| What | Command | Time |
|---|---|---|
| Demo (fake stream) | `hypecut --demo --language en` | ~2 min |
| Finished Twitch/YouTube stream | `hypecut "https://www.twitch.tv/videos/123" --out clips` | ~1 min per clip + download |
| Live stream (Ctrl+C to stop) | `pip install streamlink chat-downloader` once, then `hypecut "https://www.twitch.tv/channel" --mode live` | runs until you stop it |
| Your own recording + chat log | `hypecut stream.mp4 --chat chat.jsonl --out clips` | ~40 s per clip |
| Hindi stream, Hinglish captions | add `--language hi --hinglish` (needs the Gemini key) | |
| Only see the spikes | add `--dry-run` | seconds |

Results: open `clips\index.md`. Each `clip_XX.mp4` has a matching `clip_XX.md` with its caption.
