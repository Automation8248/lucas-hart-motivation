import requests, os, random, json, time
from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, AudioFileClip
import PIL.Image

# ---------- PIL Fix ----------
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# ================== ENV KEYS ==================
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FREESOUND_KEY = os.getenv("FREESOUND_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

AUTHOR = "Lucas Hart"
DURATION = 5
HISTORY_FILE = "quotes_history.txt"

# ================== GEMINI AI (NO FALLBACK) ==================
def get_ai_content(max_retries=10):
    prompt = f"""
Generate a UNIQUE motivational short-video content.

Rules:
- Quote max 100 characters
- Title max 40 characters
- Caption inspiring (1–2 lines)
- Exactly 8 hashtags
- Do NOT repeat previous quotes

Return ONLY valid JSON:
{{
 "title": "",
 "quote": "",
 "caption": "",
 "hashtags": ["","","","","","","",""]
}}

Author: {AUTHOR}
"""

    history = set()
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history = set(f.read().splitlines())

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            print(f"🔁 Gemini attempt {attempt}")

            res = requests.post(
                "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
                params={"key": GEMINI_API_KEY},
                headers={"Content-Type": "application/json"},
                json={"contents":[{"parts":[{"text": prompt}]}]},
                timeout=30
            )

            res.raise_for_status()

            raw = res.json()["candidates"][0]["content"]["parts"][0]["text"]

            # Remove markdown if present
            if "```" in raw:
                raw = raw.split("```")[1].strip()

            data = json.loads(raw)

            quote = data.get("quote", "").strip()

            if not quote:
                raise ValueError("Empty quote")

            if quote in history:
                raise ValueError("Repeated quote")

            if len(data.get("hashtags", [])) != 8:
                raise ValueError("Hashtag count not 8")

            with open(HISTORY_FILE, "a") as f:
                f.write(quote + "\n")

            print("✅ Gemini content approved")
            return data

        except Exception as e:
            last_error = e
            print(f"⚠️ Gemini error: {e}")
            time.sleep(1.5)

    raise RuntimeError(
        f"❌ Gemini failed after {max_retries} attempts | Last error: {last_error}"
    )

# ================== PIXABAY IMAGE ==================
def get_real_nature_img():
    res = requests.get(
        "https://pixabay.com/api/",
        params={
            "key": PIXABAY_KEY,
            "q": "nature sunrise mountain",
            "orientation": "vertical",
            "image_type": "photo",
            "per_page": 50
        },
        timeout=15
    )

    hits = res.json()["hits"]
    img_url = random.choice(hits)["largeImageURL"]
    img = requests.get(img_url).content

    with open("bg.jpg", "wb") as f:
        f.write(img)

    return "bg.jpg"

# ================== FREESOUND (SOFT PIANO) ==================
def get_soft_piano_music():
    headers = {"Authorization": f"Token {FREESOUND_KEY}"}

    queries = [
        "soft piano background",
        "calm piano instrumental",
        "emotional piano music",
        "cinematic piano soft"
    ]

    res = requests.get(
        "https://freesound.org/apiv2/search/text/",
        headers=headers,
        params={
            "query": random.choice(queries),
            "filter": "duration:[10 TO 60]",
            "fields": "previews",
            "page_size": 20
        },
        timeout=20
    )

    sound = random.choice(res.json()["results"])
    preview = sound["previews"]["preview-hq-mp3"]

    audio = requests.get(preview).content
    with open("piano.mp3", "wb") as f:
        f.write(audio)

    return "piano.mp3"

# ================== VIDEO ==================
def create_video(quote):
    bg = get_real_nature_img()
    music = get_soft_piano_music()

    image = (
        ImageClip(bg)
        .set_duration(DURATION)
        .resize(height=1920)
        .fl_image(lambda img: (img * 0.7).astype("uint8"))
    )

    text = (
        TextClip(
            f"{quote}\n\n- {AUTHOR}",
            fontsize=58,
            font="arial.ttf",
            color="white",
            method="caption",
            size=(850, None),
            align="center"
        )
        .set_position("center")
        .set_duration(DURATION)
    )

    video = CompositeVideoClip([image, text])

    audio = (
        AudioFileClip(music)
        .subclip(0, DURATION)
        .volumex(0.25)
    )

    final = video.set_audio(audio)
    final.write_videofile(
        "final_short.mp4",
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )

    return "final_short.mp4"

# ================== MAIN ==================
if __name__ == "__main__":
    data = get_ai_content()
    video = create_video(data["quote"])

    caption = (
        f"🎬 *{data['title']}*\n\n"
        f"✨ {data['caption']}\n\n"
        + " ".join(data["hashtags"])
    )

    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo",
        files={"video": open(video, "rb")},
        data={
            "chat_id": TG_CHAT_ID,
            "caption": caption,
            "parse_mode": "Markdown"
        }
    )

    print("✅ DONE — Gemini only, no fallback")

