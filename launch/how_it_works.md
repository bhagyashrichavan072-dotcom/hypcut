# How it works (for followers)

## The idea in one line
When a stream's chat suddenly explodes, something clip-worthy just happened. The tool notices that, grabs those 30 seconds and turns them into a ready-to-post vertical clip.

## The 5 steps
1. **Reads chat.** It reads Twitch or YouTube chat, live or from a finished stream's replay.
2. **Finds the spike.** It counts messages per second and compares them with the last minute. Hype words count extra: KEKW, LUL, CLIP IT, WASTED, 5 STARS, 😂, 💀. A big jump is a spike.
3. **Grabs 30 seconds.** That's 20 seconds before the spike and 10 after, because chat reacts a few seconds late.
4. **Whisper picks the best part.** Whisper is free speech-to-text AI. It writes down every word with timings, and the tool picks the best 15–30 seconds: loudest, most talking, most chat hype. It never cuts in the middle of a sentence.
5. **Makes the clip.** You get a 9:16 vertical video with word-by-word captions, a hook in the first 2.5 seconds, a title, a zoom on the big moment and chat messages flying in. With a free Gemini key, Gemini also writes the hook, title, Instagram caption and hashtags, and ranks the clips.

Every clip comes with a viral score out of 100 and a copy-paste caption.

## Setup, step by step (Windows)
1. Install Python from python.org. Tick **"Add Python to PATH"**.
2. Open PowerShell and install ffmpeg:
   `winget install Gyan.FFmpeg`
3. Download the project: on the GitHub page, click **Code → Download ZIP** and unzip it. Or use `git clone <link>`.
4. Open PowerShell inside the folder and run:
   `pip install -e .`
   (If `hypecut` is "not found" later, type `python -m hypecut` instead.)
5. Try the demo: `hypecut --demo`
   Open the `clips` folder. Your first clips are there.
6. (Optional) Get a free Gemini key at aistudio.google.com/apikey, then run:
   `$env:GEMINI_API_KEY="paste-key-here"`
7. Clip a real stream:
   `hypecut "https://www.twitch.tv/videos/..." --out clips`
   For live: `pip install streamlink chat-downloader`, then
   `hypecut "https://www.twitch.tv/channelname" --mode live`

Mac/Linux: same steps, but install ffmpeg with `brew install ffmpeg` / `sudo apt install ffmpeg` and use `export GEMINI_API_KEY=...`.

## FAQ
- **Is it free?** Yes. Whisper runs on your computer. Gemini has a free tier.
- **Does it need a good PC?** No. Any laptop works. A bigger Whisper model (`--whisper-model small`) gives better captions but runs slower.
- **Hindi or Hinglish streams?** Use `--language hi`. Add `--hinglish` (needs a Gemini key) for Roman-Hindi captions.
- **Can I clip any streamer?** Only your own streams or ones you have permission to clip. Credit the streamer.
- **Where's Google Flow?** Flow has no API, so every clip comes with a ready-to-paste Flow prompt for an AI intro shot. You paste it into Flow yourself.
