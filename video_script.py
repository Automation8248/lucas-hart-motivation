import requests, os, random, json, time
from moviepy.editor import (
    ImageClip, TextClip, CompositeVideoClip, AudioFileClip
)
from concurrent.futures import ThreadPoolExecutor
import PIL.Image

# ---------- PIL Fix ----------
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# ================== ENV KEYS ==================
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FREESOUND_KEY = os.getenv("FREESOUND_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

AUTHOR = "Lucas Hart"
DURATION = 5
HISTORY_FILE = "quotes_history.txt"

# ================== GEMINI AI ==================
def get_ai_content(max_retries=5):
    prompt = f"""
Generate a UNIQUE motivational short-video content.

Rules:
- Quote max 100 characters
- Title max 40 characters
- Caption 1–2 lines inspiring
- Exactly 8 hashtags
- Do NOT repeat old quotes

Return ONLY JSON:
{{
 "title":"",
 "quote":"",
 "caption":"",
 "hashtags":["","","","","","","",""]
}}

Author: {AUTHOR}
"""

    history = set(open(HISTORY_FILE).read().splitlines()) if os.path.exists(HISTORY_FILE) else set()

    for _ in range(max_retries):
        try:
            r = requests.post(
                "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
                params={"key": GEMINI_API_KEY},
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.8, "maxOutputTokens": 300}
                },
                timeout=30
            )

            raw = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            raw = raw.split("```")[-1]
            data = json.loads(raw)

            if data["quote"] not in history:
                with open(HISTORY_FILE, "a") as f:
                    f.write(data["quote"] + "\n")
                return data

        except Exception:
            time.sleep(1)

    return {
        "title": "Daily Motivation",
        "quote": "Small progress daily builds unstoppable success.",
        "caption": "Stay consistent. Stay focused.",
        "hashtags": ["#motivation","#success","#mindset","#goals","#focus","#growth","#discipline","#shorts"]
    }

# ================== PIXABAY IMAGE ==================
def get_real_nature_img():
    res = requests.get(
        "https://pixabay.com/api/",
        params={
            "key": PIXABAY_KEY,
            "q": "nature sunrise mountain",
            "orientation": "vertical",
            "image_type": "photo",
            "safesearch": "true",
            "per_page": 100
        },
        timeout=15
    )
    hit = random.choice(res.json()["hits"])
    img = requests.get(hit["largeImageURL"]).content

    with open("bg.jpg", "wb") as f:
        f.write(img)

    return "bg.jpg"

# ================== FREESOUND MUSIC ==================
def get_soft_piano_music():
    headers = {"Authorization": f"Token {FREESOUND_KEY}"}
    res = requests.get(
        "https://freesound.org/apiv2/search/text/",
        headers=headers,
        params={
            "query": "soft piano ambient",
            "filter": "duration:[5 TO 20]",
            "sort": "rating_desc",
            "page_size": 20
        },
        timeout=20
    )

    sound = random.choice(res.json()["results"])
    sid = sound["id"]

    info = requests.get(
        f"https://freesound.org/apiv2/sounds/{sid}/",
        headers=headers
    ).json()

    audio = requests.get(info["previews"]["preview-hq-mp3"]).content
    with open("bg_music.mp3", "wb") as f:
        f.write(audio)

    return "bg_music.mp3"

# ================== VIDEO ==================
def create_video(quote):
    bg = get_real_nature_img()
    music = get_soft_piano_music()

    clip = (
        ImageClip(bg)
        .set_duration(DURATION)
        .resize(height=1920)
        .fl_image(lambda img: (img * 0.7).astype("uint8"))
    )

    txt = (
        TextClip(
            f"{quote}\n\n- {AUTHOR}",
            fontsize=65,
            color="white",
            method="caption",
            size=(850, None)
        )
        .set_position("center")
        .set_duration(DURATION)
    )

    audio = AudioFileClip(music).volumex(0.4).set_duration(DURATION)

    video = CompositeVideoClip([clip, txt]).set_audio(audio)
    video.write_videofile("final_short.mp4", fps=24, codec="libx264", audio_codec="aac")

    return "final_short.mp4"

# ================== CATBOX ==================
def upload_catbox(video):
    r = requests.post(
        "https://catbox.moe/user/api.php",
        data={"reqtype": "fileupload"},
        files={"fileToUpload": open(video, "rb")}
    )
    return r.text.strip()

# ================== SEND ==================
def send_telegram(link, caption):
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={
            "chat_id": TG_CHAT_ID,
            "text": f"{caption}\n\n🎥 {link}",
            "parse_mode": "Markdown"
        }
    )

def send_webhook(link, data):
    requests.post(
        WEBHOOK_URL,
        json={
            "video": link,
            "title": data["title"],
            "quote": data["quote"],
            "caption": data["caption"],
            "hashtags": data["hashtags"]
        },
        timeout=15
    )

# ================== MAIN ==================
if __name__ == "__main__":
    print("🚀 Generating content...")
    data = get_ai_content()

    print("🎬 Creating video...")
    video = create_video(data["quote"])

    print("☁️ Uploading to Catbox...")
    catbox_link = upload_catbox(video)

    caption = f"🎬 *{data['title']}*\n\n✨ {data['caption']}\n\n{' '.join(data['hashtags'])}"

    with ThreadPoolExecutor(max_workers=2) as exe:
        exe.submit(send_telegram, catbox_link, caption)
        exe.submit(send_webhook, catbox_link, data)

    print("✅ Telegram + Webhook sent successfully")
