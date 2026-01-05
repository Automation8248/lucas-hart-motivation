import requests, random
from moviepy.editor import *
from PIL import Image
from telegram import Bot

# ================= CONFIG =================
PIXABAY_API_KEY = "YOUR_PIXABAY_API_KEY"
FREESOUND_API_KEY = "YOUR_FREESOUND_API_KEY"
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"
WEBHOOK_URL = "YOUR_WEBHOOK_URL"

AUTHOR = "Lucas Hart"
DURATION = 5

# ================= ENGLISH POST TEXT =================
TITLES = [
    "Daily Motivation",
    "One Thought Can Change Everything",
    "Start Your Day With Purpose",
    "Pause And Reflect"
]

CAPTIONS = [
    "Let this message guide your mindset today.",
    "Consistency creates success. Keep moving forward.",
    "A small thought today can create a big change tomorrow.",
    "Stay focused. Stay disciplined. Stay unstoppable."
]

HASHTAGS = [
    "#motivation",
    "#dailyquotes",
    "#mindset",
    "#success",
    "#inspiration",
    "#selfgrowth",
    "#positivevibes",
    "#dailymotivation"
]

# ================= QUOTE FETCH (FREE WEBSITE) =================
def get_quote():
    r = requests.get("https://zenquotes.io/api/random", timeout=10).json()
    quote = r[0]["q"]
    if len(quote) < 50:
        return get_quote()
    return f"{quote}\n\n— {AUTHOR}"

# ================= PIXABAY IMAGE =================
def fetch_image():
    url = f"https://pixabay.com/api/?key={PIXABAY_API_KEY}&q=nature&orientation=vertical&per_page=50"
    data = requests.get(url).json()
    img = random.choice(data["hits"])
    open("bg.jpg", "wb").write(requests.get(img["largeImageURL"]).content)

# ================= FREESOUND MUSIC =================
def fetch_music():
    headers = {"Authorization": f"Token {FREESOUND_API_KEY}"}
    params = {
        "query": "soft piano",
        "filter": "duration:[5 TO 15]",
        "fields": "previews"
    }
    r = requests.get(
        "https://freesound.org/apiv2/search/text/",
        headers=headers,
        params=params
    ).json()
    music_url = random.choice(r["results"])["previews"]["preview-hq-mp3"]
    open("music.mp3", "wb").write(requests.get(music_url).content)

# ================= VIDEO CREATE =================
def create_video(text):
    Image.open("bg.jpg").resize((1080,1920)).save("bg_r.jpg")
    bg = ImageClip("bg_r.jpg").set_duration(DURATION)

    txt = TextClip(
        text,
        fontsize=60,
        color="white",
        method="caption",
        size=(900,None),
        align="center"
    ).set_position("center").set_duration(DURATION).fadein(0.5)

    audio = AudioFileClip("music.mp3").subclip(0,DURATION).volumex(0.4)
    video = CompositeVideoClip([bg, txt]).set_audio(audio)
    video.write_videofile("final.mp4", fps=30)

# ================= CATBOX UPLOAD =================
def upload_catbox():
    r = requests.post(
        "https://catbox.moe/user/api.php",
        data={"reqtype":"fileupload"},
        files={"fileToUpload":open("final.mp4","rb")}
    )
    return r.text.strip()

# ================= TELEGRAM =================
def send_telegram(url):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    msg = (
        f"{random.choice(TITLES)}\n\n"
        f"{random.choice(CAPTIONS)}\n\n"
        f"{url}\n\n"
        f"{' '.join(HASHTAGS)}"
    )
    bot.send_message(chat_id=CHAT_ID, text=msg)

# ================= WEBHOOK =================
def send_webhook(url):
    payload = {
        "title": random.choice(TITLES),
        "caption": random.choice(CAPTIONS),
        "video": url,
        "hashtags": HASHTAGS,
        "language": "en"
    }
    requests.post(WEBHOOK_URL, json=payload)

# ================= MAIN =================
def main():
    quote = get_quote()
    fetch_image()
    fetch_music()
    create_video(quote)
    url = upload_catbox()
    send_telegram(url)
    send_webhook(url)

if __name__ == "__main__":
    main()

