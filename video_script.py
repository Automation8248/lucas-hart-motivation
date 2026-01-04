import requests, os, random, json
from moviepy.editor import ImageClip, TextClip, AudioFileClip, CompositeVideoClip, ColorClip

# API Keys from GitHub Secrets
PIXABAY_KEY = os.getenv('PIXABAY_API_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_API_KEY')
OPENROUTER_KEY = os.getenv('OPENROUTER_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

AUTHOR = "Lucas Hart"
DURATION = 5  # Video duration set to 5 seconds

def get_ai_quote():
    """OpenRouter se unique quote lena (No stars, No labels)"""
    prompt = f"Write one unique short motivational quote by {AUTHOR}. Max 45 characters. Provide ONLY the quote text, no labels like 'Quote:' or stars."
    res = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
        json={"model": "google/gemini-2.0-flash-exp:free", "messages": [{"role": "user", "content": prompt}]}
    )
    res.raise_for_status()
    quote = res.json()['choices'][0]['message']['content'].strip()
    return quote.replace("*", "").replace('"', "").strip()

def get_unique_nature_img():
    """Pixabay se nature image lena aur repetition rokna"""
    url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q=nature+landscape&orientation=vertical&per_page=100"
    hits = requests.get(url).json()['hits']
    
    if os.path.exists("video_history.txt"):
        with open("video_history.txt", "r") as f: history = f.read().splitlines()
    else: history = []

    for hit in hits:
        if str(hit['id']) not in history:
            with open("video_history.txt", "a") as f: f.write(str(hit['id']) + "\n")
            with open('bg.jpg', 'wb') as f: f.write(requests.get(hit['largeImageURL']).content)
            return 'bg.jpg'
    return None

def create_video(quote_text):
    """Image, Highlighted Text aur Music ko merge karna"""
    # Background Image
    bg_img = get_unique_nature_img()
    clip = ImageClip(bg_img).set_duration(DURATION).resize(height=1920) # Shorts Size (9:16)
    
    # Shadow Box for Highlighting (Halka black parda text ke niche)
    shadow = ColorClip(size=(900, 400), color=(0,0,0)).set_opacity(0.5).set_duration(DURATION).set_position('center')

    # Highlighted Text (Bada size aur stroke)
    full_display = f"{quote_text}\n\n- {AUTHOR}"
    txt_clip = TextClip(full_display, fontsize=75, color='white', font='Arial-Bold', 
                        method='caption', size=(800, None), align='Center',
                        stroke_color='black', stroke_width=2).set_duration(DURATION).set_position('center')
    
    # Piano Music from Freesound
    m_url = f"https://freesound.org/apiv2/search/text/?query=piano+soft&token={FREESOUND_KEY}"
    s_id = requests.get(m_url).json()['results'][0]['id']
    sound_info = requests.get(f"https://freesound.org/apiv2/sounds/{s_id}/?token={FREESOUND_KEY}").json()
    with open('music.mp3', 'wb') as f: f.write(requests.get(sound_info['previews']['preview-hq-mp3']).content)
    
    audio = AudioFileClip('music.mp3').subclip(0, DURATION)
    
    # Final Merge
    video = CompositeVideoClip([clip, shadow, txt_clip]).set_audio(audio)
    video.write_videofile("final_short.mp4", fps=24, codec="libx264", audio_codec="aac")
    return "final_short.mp4"

def upload_to_catbox(file):
    """Final Video ko Catbox par upload karna"""
    with open(file, 'rb') as f:
        res = requests.post("https://catbox.moe/user/api.php", data={'reqtype': 'fileupload'}, files={'fileToUpload': f})
    return res.text.strip()

# Main Sequence
try:
    print("Fetching AI Quote...")
    quote = get_ai_quote()
    
    print("Creating Merged Video...")
    video_file = create_video(quote)
    
    print("Uploading to Catbox...")
    catbox_url = upload_to_catbox(video_file)
    print(f"URL: {catbox_url}")

    if "http" in catbox_url:
        # Title/Caption control (Max 50 chars) aur 8 Hashtags
        caption = f"✨ {quote[:48]}\n\n#motivation #lucashart #shorts #nature #quotes #success #inspiration #mindset"
        
        # Telegram Post
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", 
                      data={"chat_id": TG_CHAT_ID, "video": catbox_url, "caption": caption}).raise_for_status()
        
        # Webhook Post
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"video_url": catbox_url, "caption": caption})
            
        print("Successfully Sent to Telegram and Webhook!")
    else:
        print("Catbox Upload Failed!")

except Exception as e:
    print(f"Error occurred: {e}")
    exit(1)
