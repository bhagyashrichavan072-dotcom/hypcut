# v0.1.0: chat spikes → vertical clips

First release.

**What it does:** it watches Twitch or YouTube chat, detects hype spikes (weighted messages/sec vs a rolling baseline) and grabs the 30 s around each one. Whisper then picks the best 15–30 s cut, snapped to sentence edges, and the tool renders a 9:16 clip with word-by-word captions, a hook card, a title, a punch-zoom and chat pop-ups.

- Modes: `vod` (Twitch/YouTube; downloads only the spike windows), `live` (rolling buffer), `file` (local video + chat log), `--demo`, `--dry-run`
- Whisper backends: faster-whisper (default) or whisper.cpp (`--whisper-cpp`)
- Optional Gemini step (`GEMINI_API_KEY`): ranks clips and writes the hook, title, caption and hashtags; Hinglish captions with `--hinglish`
- Works with no key: offline hooks and captions, plus a 0–100 hook score and viral score
- Ready-to-paste Google Flow prompt per clip (Flow has no API)
- Per clip: `.mp4`, `.md`, `.json`; plus `index.md` and `AGENT_BRIEF.md`

**Known limits:** live mode and Twitch VOD chat are new and lightly tested. Chat/video sync in live mode is approximate (`--sync-offset`).

Clip only streams you own or have permission to clip.
