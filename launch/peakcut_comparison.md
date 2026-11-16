# PeakCut vs our clipper: what we took

PeakCut (github.com/haziqahmedqasmi/PeakCut, MIT) is a full self-hosted web app: FastAPI, a dashboard, workspaces, accounts, auto-posting to YT/IG/TikTok, and Parakeet speech-to-text (a 480 MB model). The AI picks moments from the transcript; live mode uses loudness + chat + transcript.

## Taken (ideas only, our own code)
- **AI models tried in order** with a fallback list (`--gemini-model "a,b"`).
- **Works without a key:** offline hooks, captions and scores, so nobody is blocked.
- **Transcripts and chat sent as data:** the prompt tells the model to ignore instructions inside them (prompt-injection defence).
- **Hook on the clip + caption styles** (`--caption-style bold|clean|box`).
- **Credits** in the README.

## Where we're different (use these in the pitch)
- **Chat is the main signal**, not a side input: z-score spikes with GTA and Twitch hype-word weights. That makes it built for streams, not podcasts.
- **One command, no server, no accounts.** `hypecut --demo` works in a minute.
- **Downloads only the spike windows** from VODs, not the whole stream.
- **0–100 viral score + hook score** per clip, plus a copy-paste post caption.
- **Hinglish captions** (`--hinglish`) for Indian creators.
- **Google Flow prompt** per clip for an AI intro shot.

## Worth adding later (not built)
- Auto-posting to IG/YT/TikTok (PeakCut has it; it needs OAuth apps, so it's a big job)
- Face-tracking crop for facecam streams
- A small web UI
- Bundled caption fonts (Anton / Archivo Black, OFL licence)
- Kick chat
