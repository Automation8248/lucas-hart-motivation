import requests, os, random, json, time
from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, AudioFileClip
from concurrent.futures import ThreadPoolExecutor
import PIL.Image

# ---------- PIL FIX ----------
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# ================== ENV ==================
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FREESOUND_KEY = os.getenv("FREESOUND_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

AUTHOR = "Lucas Hart"
DURATION = 5
HISTORY_FILE = "quotes_history.txt"

# ================== GEMINI (FORCED) ==================
def get_ai_content():
    prompt = f"""
Generate a UNIQUE motivational short-video content.

Rules:
- Quote must be motivational (max 100 chars)
- Title max 40 chars
- Caption 1–2 inspiring lines
- Exactly 8 hashtags
- Never repeat old quotes
- Output ONLY JSON

Format:
{{
 "title":"",
 "quote":"",
 "caption":"",
 "hashtags":["","","","","","","",""]
}}

Author: {AUTHOR}
"""

    history = set(open(HISTORY_FILE).read().splitlines()) if os.path.exists(HISTORY_FILE) else set()

    while True:
        try:
            res = requests.post(
                "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
                params={"key": GEMINI_API_KEY},
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.9, "maxOutputTokens": 300}
                },
                timeout=30
            )

            raw = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            raw = raw.split("```")[-1].strip()
            data = json.loads(raw)

            quote = data.get("quote", "").strip()
            if not quote or quote in history:
                raise ValueError("Invalid or duplicate quote")

            with open(HISTORY_FILE, "a") as f:
                f.write(quote + "\n")

            return data

        except Exception as e:
            print("Retry Gemini:", e)
            time.sleep(1)

# ================== PIXABAY IMAGE ==================
def get_image():
    r = requests.get(
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
    img_url = random.choice(r.json()["hits"])["largeImageURL"]
    img = requests.get(img_url).content

    with open("bg.jpg", "wb") as f:
        f.write(img)

    return "bg.jpg"

# ================== FREESOUND MUSIC ==================
def get_music():
    headers = {"Authorization": f"Token {FREESOUND_KEY}"}
    r = requests.get(
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

    sound = random.choice(r.json()["results"])
    sid = sound["id"]

    info = requests.get(
        f"https://freesound.org/apiv2/sounds/{sid}/",
        headers=headers
    ).json()

    audio = requests.get(info["previews"]["preview-hq-mp3"]).content
    with open("music.mp3", "wb") as f:
        f.write(audio)

    return "music.mp3"

# ================== VIDEO ==================
def create_video(quote):
    bg = get_image()
    music = get_music()

    img_clip = (
        ImageClip(bg)
        .set_duration(DURATION)
        .resize(height=1920)
        .fl_image(lambda i: (i * 0.7).astype("uint8"))
    )

    txt_clip = (
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

    video = CompositeVideoClip([img_clip, txt_clip]).set_audio(audio)
    video.write_videofile(
        "final.mp4",
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )

    return "final.mp4"

# ================== CATBOX ==================
def upload_catbox(path):
    r = requests.post(
        "https://catbox.moe/user/api.php",
        data={"reqtype": "fileupload"},
        files={"fileToUpload": open(path, "rb")}
    )
    return r.text.strip()

# ================== SEND ==================
def send_telegram(video, caption):
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo",
        files={"video": open(video, "rb")},
        data={
            "chat_id": TG_CHAT_ID,
            "caption": caption,
            "parse_mode": "Markdown"
        }
    )

def send_webhook(link):
    requests.post(
        WEBHOOK_URL,
        json={"video_url": link},
        timeout=15
    )

# ================== MAIN ==================
if __name__ == "__main__":
    print("🤖 Gemini generating...")
    data = get_ai_content()

    print("🎬 Creating video...")
    video = create_video(data["quote"])

    print("☁️ Uploading to Catbox...")
    catbox_link = upload_catbox(video)

    telegram_caption = (
        f"🎬 *{data['title']}*\n\n"
        f"{data['caption']}\n\n"
        f"{' '.join(data['hashtags'])}"
    )

    with ThreadPoolExecutor(max_workers=2) as ex:
        ex.submit(send_telegram, video, telegram_caption)
        ex.submit(send_webhook, catbox_link)

    print("✅ DONE: Telegram video + Webhook link sent")

