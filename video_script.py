import requests, os, random, json, time
from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, AudioFileClip
import PIL.Image

# ---------- PIL Fix ----------
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# ================== ENV KEYS ==================
PIXABAY_KEY = os.getenv('PIXABAY_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
FREESOUND_API_KEY = os.getenv('FREESOUND_API_KEY')

TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

AUTHOR = "Lucas Hart"
DURATION = 5
HISTORY_FILE = "quotes_history.txt"

# ================== AI CONTENT WITH ERROR HANDLING ==================
def get_ai_content(max_retries=5):
    prompt = f"""
Generate UNIQUE motivational content.

Rules:
- Quote max 100 characters
- Title max 40 characters
- Caption 1–2 inspiring lines
- EXACTLY 8 motivational hashtags
- Do NOT repeat previous quotes

Return ONLY valid JSON:
{{
  "title": "",
  "quote": "",
  "caption": "",
  "hashtags": ["", "", "", "", "", "", "", ""]
}}

Author: {AUTHOR}
"""

    for attempt in range(max_retries):
        try:
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta-llama/llama-3-8b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 300
                },
                timeout=30
            )

            data = res.json()

            if "choices" not in data or not data["choices"]:
                raise ValueError("No choices in response")

            raw = data["choices"][0]["message"].get("content", "").strip()
            if not raw:
                raise ValueError("Empty AI response")

            # Remove code block ticks if present
            if "```" in raw:
                raw = raw.split("```")[1].strip()

            parsed = json.loads(raw)

            if (
                "quote" in parsed and
                "title" in parsed and
                "caption" in parsed and
                isinstance(parsed.get("hashtags"), list) and
                len(parsed["hashtags"]) == 8
            ):
                # Save quote history
                if os.path.exists(HISTORY_FILE):
                    history = set(open(HISTORY_FILE).read().splitlines())
                else:
                    history = set()

                if parsed["quote"] not in history:
                    with open(HISTORY_FILE, "a") as f:
                        f.write(parsed["quote"] + "\n")

                return parsed

        except Exception as e:
            print(f"AI Retry {attempt+1} failed:", e)
            time.sleep(2)

    # Fallback if AI fails
    return {
        "title": "Daily Motivation",
        "quote": "Small steps every day create massive change.",
        "caption": "Stay consistent. Your future self will thank you.",
        "hashtags": [
            "#motivation", "#success", "#mindset", "#goals",
            "#focus", "#growth", "#discipline", "#inspiration"
        ]
    }

# ================== GET BACKGROUND IMAGE ==================
def get_bg_image():
    r = requests.get(
        "https://pixabay.com/api/",
        params={
            "key": PIXABAY_KEY,
            "q": "nature sunrise mountain",
            "orientation": "vertical",
            "image_type": "photo",
            "per_page": 50,
            "safesearch": "true"
        }
    )
    hits = r.json().get("hits", [])
    if not hits:
        raise Exception("No images found from Pixabay")

    img_url = random.choice(hits)["largeImageURL"]
    img = requests.get(img_url).content

    with open("bg.jpg", "wb") as f:
        f.write(img)

    return "bg.jpg"

# ================== GET FREESOUND MUSIC ==================
def get_music():
    headers = {"Authorization": f"Token {FREESOUND_API_KEY}"}
    r = requests.get(
        "https://freesound.org/apiv2/search/text/",
        headers=headers,
        params={
            "query": "motivational cinematic",
            "filter": "duration:[10 TO 60]",
            "page_size": 10
        }
    )
    results = r.json().get("results", [])
    if not results:
        raise Exception("No sounds found from Freesound")

    sound_id = random.choice(results)["id"]
    data = requests.get(
        f"https://freesound.org/apiv2/sounds/{sound_id}/",
        headers=headers
    ).json()

    preview_url = data["previews"]["preview-hq-mp3"]
    audio = requests.get(preview_url).content
    with open("music.mp3", "wb") as f:
        f.write(audio)

    return "music.mp3"

# ================== CREATE VIDEO ==================
def create_video(quote):
    bg = get_bg_image()
    music = get_music()

    clip = (
        ImageClip(bg)
        .set_duration(DURATION)
        .resize(height=1920)
        .fl_image(lambda i: (i * 0.7).astype("uint8"))
    )

    txt = (
        TextClip(
            f"{quote}\n\n- {AUTHOR}",
            fontsize=60,
            color="white",
            font="Arial",
            method="caption",
            size=(850, None)
        )
        .set_position("center")
        .set_duration(DURATION)
    )

    audio = AudioFileClip(music).volumex(0.4).subclip(0, DURATION)

    video = CompositeVideoClip([clip, txt]).set_audio(audio)
    video.write_videofile("final_short.mp4", fps=24, codec="libx264")

    return "final_short.mp4"

# ================== UPLOAD TO CATBOX ==================
def upload_to_catbox(path):
    with open(path, "rb") as f:
        r = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": f}
        )
    if r.status_code == 200 and r.text.startswith("http"):
        return r.text.strip()
    else:
        raise Exception("Catbox upload failed")

# ================== SEND WEBHOOK ==================
def send_webhook(webhook_url, video_url):
    requests.post(webhook_url, json={"content": video_url}, timeout=10)

# ================== MAIN ==================
if __name__ == "__main__":
    data = get_ai_content()

    video_path = create_video(data["quote"])
    catbox_link = upload_to_catbox(video_path)

    # Webhook gets ONLY the link
    if WEBHOOK_URL:
        send_webhook(WEBHOOK_URL, catbox_link)

    # Telegram gets the video + caption (title, caption, hashtags)
    telegram_caption = (
        f"🎬 *{data['title']}*\n\n"
        f"{data['caption']}\n\n"
        f"{' '.join(data['hashtags'])}"
    )

    with open(video_path, "rb") as video_file:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo",
            data={
                "chat_id": TG_CHAT_ID,
                "caption": telegram_caption,
                "parse_mode": "Markdown"
            },
            files={"video": video_file}
        )

    print("✅ ALL DONE")

