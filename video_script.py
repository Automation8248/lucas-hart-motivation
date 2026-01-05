import requests, os, random, json, time
from moviepy.editor import ImageClip, TextClip, CompositeVideoClip
import PIL.Image

# ---------- PIL Fix ----------
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# ================== ENV KEYS ==================
PIXABAY_KEY = os.getenv('PIXABAY_API_KEY')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

AUTHOR = "Lucas Hart"
DURATION = 5
HISTORY_FILE = "quotes_history.txt"

# ================== AI DATA (OpenRouter FREE) ==================
def get_ai_content(max_retries=5):

    prompt = f"""
Generate a UNIQUE motivational short-video content.

Rules:
- Quote max 100 characters
- Title max 40 characters
- Caption should be inspiring (1–2 lines)
- Exactly 8 hashtags
- Hashtags must be short & trending
- Do NOT repeat previous quotes

Return ONLY valid JSON in this format:
{{
  "title": "",
  "quote": "",
  "caption": "",
  "hashtags": ["", "", "", "", "", "", "", ""]
}}

Author name to include: {AUTHOR}
"""

    history = set(open(HISTORY_FILE).read().splitlines() if os.path.exists(HISTORY_FILE) else [])

    for attempt in range(max_retries):
        try:
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://example.com",
                    "X-Title": "AI Motivation Shorts"
                },
                json={
                    "model": "meta-llama/llama-3-8b-instruct",  # FREE
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 300
                },
                timeout=30
            )

            raw = res.json()["choices"][0]["message"]["content"].strip()

            if "```" in raw:
                raw = raw.split("```")[1]

            data = json.loads(raw)
            quote = data["quote"].strip()

            if quote and quote not in history:
                with open(HISTORY_FILE, "a") as f:
                    f.write(quote + "\n")
                return data

        except Exception as e:
            print(f"AI Attempt {attempt+1} Error:", e)
            time.sleep(1)

    # Fallback
    return {
        "title": "Daily Motivation",
        "quote": "Discipline today builds unstoppable success tomorrow.",
        "caption": "Stay focused. Stay consistent. Results will follow.",
        "hashtags": ["#motivation", "#success", "#mindset", "#goals", "#discipline", "#focus", "#growth", "#shorts"]
    }

# ================== PIXABAY IMAGE ==================
def get_real_nature_img():
    url = "https://pixabay.com/api/"
    params = {
        "key": PIXABAY_KEY,
        "q": "nature landscape mountain sunrise",
        "orientation": "vertical",
        "image_type": "photo",
        "per_page": 100,
        "safesearch": "true"
    }

    res = requests.get(url, params=params, timeout=15)
    hits = res.json().get("hits", [])
    random.shuffle(hits)

    img = requests.get(hits[0]["largeImageURL"]).content
    with open("bg.jpg", "wb") as f:
        f.write(img)

    return "bg.jpg"

# ================== VIDEO ==================
def create_video(quote):
    bg = get_real_nature_img()

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

    video = CompositeVideoClip([clip, txt])
    video.write_videofile("final_short.mp4", fps=24, codec="libx264")

    return "final_short.mp4"

# ================== MAIN ==================
if __name__ == "__main__":
    print("Generating AI content...")
    data = get_ai_content()

    title = data["title"]
    quote = data["quote"]
    caption_text = data["caption"]
    hashtags = " ".join(data["hashtags"])

    print("Creating video...")
    video_file = create_video(quote)

    caption = f"🎬 *{title}*\n\n✨ {caption_text}\n\n{hashtags}"

    print("Uploading to Telegram...")
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo",
        data={
            "chat_id": TG_CHAT_ID,
            "video": open(video_file, "rb"),
            "caption": caption,
            "parse_mode": "Markdown"
        }
    )

    print("✅ DONE")

