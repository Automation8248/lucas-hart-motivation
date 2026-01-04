import requests, os, random, json, time

# PIL Fix for moviepy compatibility
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import ImageClip, TextClip, AudioFileClip, CompositeVideoClip

# ================== ENV KEYS ==================
PIXABAY_KEY = os.getenv('PIXABAY_API_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')  # Use Gemini key here
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

AUTHOR = "Lucas Hart"
DURATION = 5

# ================== AI DATA (Gemini) ==================
def get_ai_data():
    """
    Fetches a fresh motivational quote and title from Gemini Generative Language API.
    Returns (title, quote)
    """
    prompt = (
        f"Generate a unique motivational quote by {AUTHOR} (max 100 chars) "
        f"and a catchy title (max 40 chars). "
        f"Return ONLY JSON: {{\"title\":\"...\",\"quote\":\"...\"}}"
    )

    try:
        res = requests.post(
            "https://generativelanguage.googleapis.com/v1beta2/models/text-bison-001:generateMessage",
            headers={
                "Authorization": f"Bearer {GEMINI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "prompt": {"text": prompt},
                "temperature": 0.7,
                "maxOutputTokens": 256
            },
            timeout=25
        )

        raw = res.json()["candidates"][0]["content"].strip()

        # Remove code fences if present
        if "```" in raw:
            raw = raw.split("```")[1]

        data = json.loads(raw)
        return data.get('title', 'Daily Inspiration'), data.get('quote', 'Success starts with self-discipline.')

    except Exception as e:
        print("AI Error:", e)
        return "Daily Inspiration", "Success starts with self-discipline."

# ================== PIXABAY IMAGE ==================
def get_real_nature_img():
    """
    Fetches a nature photo from Pixabay that is real (no illustrations, no vector graphics)
    """
    url = "https://pixabay.com/api/"
    params = {
        "key": PIXABAY_KEY,
        "q": "nature landscape mountain forest river lake waterfall sunset",
        "orientation": "vertical",
        "per_page": 100,
        "safesearch": "true",
        "image_type": "photo"
    }

    try:
        res = requests.get(url, params=params, timeout=15)
        res.raise_for_status()
        hits = res.json().get("hits", [])

        if not hits:
            print("No real photos found.")
            return None

        history_file = "image_history.txt"
        history = open(history_file).read().splitlines() if os.path.exists(history_file) else []

        random.shuffle(hits)
        for h in hits:
            if str(h['id']) not in history:
                img = requests.get(h['largeImageURL'], timeout=15).content
                with open("bg.jpg", "wb") as f:
                    f.write(img)
                with open(history_file, "a") as f:
                    f.write(str(h['id']) + "\n")
                return "bg.jpg"

    except Exception as e:
        print("Pixabay Error:", e)

    return None

# ================== VIDEO ==================
def create_video(quote):
    bg = get_real_nature_img()
    if not bg:
        raise Exception("Image download failed")

    clip = (
        ImageClip(bg)
        .set_duration(DURATION)
        .resize(height=1920)
        .fl_image(lambda img: (img * 0.7).astype("uint8"))
    )

    text = f"{quote}\n\n- {AUTHOR}"
    txt = (
        TextClip(
            text,
            fontsize=65,
            color="white",
            font="Arial-Bold",
            method="caption",
            size=(850, None),
        )
        .set_position("center")
        .set_duration(DURATION)
    )

    # ---------- AUDIO ----------
    audio = None
    try:
        search = requests.get(
            "https://freesound.org/apiv2/search/text/",
            params={"query": "piano soft", "token": FREESOUND_KEY},
            timeout=10
        ).json()

        s_id = search["results"][0]["id"]

        info = requests.get(
            f"https://freesound.org/apiv2/sounds/{s_id}/",
            params={"token": FREESOUND_KEY},
            timeout=10
        ).json()

        with open("music.mp3", "wb") as f:
            f.write(requests.get(info["previews"]["preview-hq-mp3"]).content)

        audio = AudioFileClip("music.mp3").subclip(0, DURATION)
    except:
        pass

    video = CompositeVideoClip([clip, txt])
    if audio:
        video = video.set_audio(audio)

    video.write_videofile(
        "final_short.mp4",
        fps=24,
        codec="libx264",
        audio_codec="aac"
    )

    return "final_short.mp4"

# ================== MAIN ==================
if __name__ == "__main__":
    try:
        # ---------- STEP 1: Get new motivational quote ----------
        print("Step 1: Fetch AI motivational quote")
        title, quote = get_ai_data()
        print(f"Quote: {quote}")

        # ---------- STEP 2: Create video ----------
        print("Step 2: Generate video")
        video_file = create_video(quote)

        # ---------- STEP 3: Upload to Catbox ----------
        print("Step 3: Upload to Catbox")
        with open(video_file, "rb") as f:
            catbox_url = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f}
            ).text.strip()

        if "http" not in catbox_url:
            raise Exception("Catbox upload failed")

        caption = (
            f"🎬 *{title}*\n\n"
            f"✨ {quote}\n\n"
            f"#motivation #nature #shorts #lucashart #success #mindset"
        )

        # ---------- TELEGRAM ----------
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo",
            data={
                "chat_id": TG_CHAT_ID,
                "video": catbox_url,
                "caption": caption,
                "parse_mode": "Markdown"
            }
        )

        # ---------- WEBHOOK ----------
        if WEBHOOK_URL:
            requests.post(
                WEBHOOK_URL,
                json={"url": catbox_url, "title": title, "caption": caption},
                timeout=10
            )

        print("SUCCESS:", catbox_url)

    except Exception as e:
        print("Fatal Error:", e)

