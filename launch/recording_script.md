# HypeCut launch video: shoot plan + script (≈45 s, Hinglish)

**What you record**
- **CAM** = you on camera (face, desk, laptop visible).
- **SCREEN** = laptop screen recording of the HypeCut app (Windows: Win+Alt+R with Xbox Game Bar, or OBS).

**Before you hit record**
1. Open HypeCut from the Desktop icon. Close other windows.
2. Pick one finished Twitch/YouTube stream that has an active chat (one you're allowed to clip). Copy its link.
3. Do one run beforehand so the **My clips** tab already has 6 good clips to show (a run takes a few minutes; you'll cut that wait out).
4. Don't show your Gemini key or the Settings tab on screen.

---

| # | Time | Shot | You say (Hinglish) | On-screen text |
|---|---|---|---|---|
| 1 | 0:00–0:03 | CAM, close, fast push-in | "Streamers, aapka chat already bata raha hai kaunsa moment viral hoga." | **YOUR CHAT KNOWS** |
| 2 | 0:03–0:07 | CAM → cut to SCREEN: HypeCut opening | "Isliye maine banaya HypeCut. Ek app jo chat padh ke khud clips banata hai." | **HYPECUT** + logo |
| 3 | 0:07–0:12 | SCREEN: paste link in Video link, click Start | "Bas stream ka link paste karo, Start dabao." | **1. PASTE LINK** |
| 4 | 0:12–0:18 | SCREEN: Runs box with spikes scrolling (speed up 4x) | "HypeCut poora chat scan karta hai. Jahan chat phat jaata hai, KEKW, CLIP IT, wahi moment pakadta hai." | **2. CHAT SPIKE = MOMENT** |
| 5 | 0:18–0:24 | SCREEN: My clips tab, 6 clips grid | "Har run mein 6 alag clips. Har clip ek alag moment se, repeat nahi." | **3. 6 CLIPS EVERY RUN** |
| 6 | 0:24–0:31 | SCREEN: play one clip full screen (hook, title, captions, zoom) | "Vertical 9:16, word-by-word captions, hook, title, zoom, sab automatic." | **4. READY TO POST** |
| 7 | 0:31–0:37 | SCREEN: point at viral score, click Copy caption | "Har clip ka viral score, aur Instagram caption plus hashtags, ek click mein copy." | **5. VIRAL SCORE + CAPTION** |
| 8 | 0:37–0:41 | CAM, Founder tab visible on laptop behind you | "Sab kuch aapke laptop pe chalta hai. Free." | **RUNS ON YOUR LAPTOP** |
| 9 | 0:41–0:45 | CAM, direct to lens | "Comment karo CLIP, main link DM kar dunga." | **COMMENT "CLIP"** |

**B-roll to grab while you're at it (5–10 s each):** typing the link, the Start button press, the Runs log scrolling, scrolling through My clips, a clip playing, the Founder tab, the desktop icon double-click.

**Keep out of the video:** pricing, trial, limits, Pro (those come after launch), the Settings tab with your key, and any real streamer's footage you don't have permission to show (blur it or use the Demo run).

---

# How to use HypeCut (for your followers)
*Use this as the DM reply, the pinned comment or the caption text.*

**Install (one time, ~10 min)**
1. Install **Python** from python.org. Tick **"Add Python to PATH"** during setup.
2. Install **ffmpeg**: open PowerShell and run `winget install Gyan.FFmpeg`
3. Download HypeCut from GitHub: **Code → Download ZIP**, then unzip it.
4. Open PowerShell in the unzipped folder and run `pip install -e .`
5. Make the desktop icon: `python -m hypecut app --shortcut`

**Use it**
1. Double-click the **HypeCut** icon.
2. **Clip** tab → **Video link** (finished stream) or **Channel (live)** → paste the link → **Start clipping**.
3. Watch progress in **Runs**.
4. Open **My clips**: play, **Download**, **Copy caption + hashtags**, post.
5. Run the same video again for 6 new moments.

**Tips**
- Try **Demo** first: it works without the internet.
- Optional: add a free Gemini key in **Settings** for smarter hooks and captions.
- Only clip your own streams or streams you have permission to clip.
