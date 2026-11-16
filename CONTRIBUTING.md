# Contributing

Bug reports and pull requests are welcome. By contributing you agree to the Contributions section of the LICENSE. Keep it simple: plain Python + ffmpeg, no heavy frameworks.

- Try your change on the demo: `hypecut --demo --no-gemini`
- New hype words / emotes: add them to `HYPE_WORDS` in `hypecut/spikes.py` with a weight (1 = normal, 4 = "clip it").
- New chat formats: add a loader in `hypecut/chat.py` that returns `ChatMessage(t, user, text)`.
- Ideas we'd love: face-tracking crop, more chat sources (Kick), a small web UI, better Hindi captions.
- Never commit stream footage you don't own.
