# HypeCut: install guide + video script

## A. How followers install HypeCut (Windows)

**Option 1: let Claude Code do it (easiest)**
Open Claude Code and paste:
> Install HypeCut for me from https://github.com/<you>/hypecut . Install Python 3.10+ and ffmpeg if they're missing, clone the repo, run `pip install -e .` inside it, then run `python -m hypecut app --shortcut` and open the app with `python -m hypecut app`.

**Option 2: by hand (~10 min)**
1. Install **Python** from python.org and tick **"Add Python to PATH"**.
2. Open **PowerShell** and install ffmpeg:
   `winget install Gyan.FFmpeg`
3. On the GitHub page click **Code → Download ZIP**, then unzip it.
4. Open PowerShell in that folder and run:
   `pip install -e .`
5. Make the desktop icon:
   `python -m hypecut app --shortcut`
6. Double-click **HypeCut** on the Desktop.
7. Optional: paste a free Gemini key (aistudio.google.com/apikey) in **Settings** for smarter hooks and captions.

**Using it**
1. **Clip** tab → paste a **Video link** (or **Channel** for live, or **My files**) → **Start clipping**.
2. The progress bar shows each step and the minutes left.
3. **My clips**: play, **Download**, **Copy caption + hashtags**, **Delete**.
4. Run the same video again for 6 new moments.

**How long it takes (6 clips, 720p)**
| Video | Time |
|---|---|
| 15 min | ~5 min |
| 1 hour | ~8–15 min (talking videos take the longest) |
| 3 hours | ~15–45 min |
Online links add download time.

---

## B. Screen-recording script (~45 s, Hinglish)
You only record the screen and say the lines. Text, zooms and music go in the edit.

**Before recording:** open HypeCut, do one run first so My clips has 6 clips, and keep the Settings tab with your key off screen.

| # | On screen | You say |
|---|---|---|
| 1 | Double-click the HypeCut icon; the app opens full screen | "Ye hai HypeCut. Free hai, aur aapke laptop pe chalta hai." |
| 2 | Paste a link in **Video link** | "Kisi bhi stream ya video ka link paste karo." |
| 3 | Click **Start clipping**; the progress bar moves | "Start dabao. HypeCut khud dhundta hai video ke best moments." |
| 4 | Point at the progress text | "Chat hai to chat ke spikes se, chat nahi hai to video ki hype se, aur podcast ho to best stories se." |
| 5 | Open **My clips** and scroll through 6 clips | "Har run mein 6 alag clips. Repeat nahi." |
| 6 | Play one clip | "Vertical, captions, hook, title, face tracking: sab automatic." |
| 7 | Point at the viral score, click **Copy caption + hashtags** | "Har clip ka viral score, aur caption plus hashtags ek click mein." |
| 8 | Click **Download** | "Download karo, post karo." |
| 9 | Open **Settings**, Gemini key box (empty) | "Bas ek free Gemini API key chahiye." |
| 10 | Back to **Clip** | "Comment karo CLIP, main GitHub link DM kar dunga." |

**Keep out of the recording:** your real Gemini key, the Developer tab, pricing and trial, and other streamers' footage without permission.
