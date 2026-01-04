import requests, os, random, json, time

# Mistake 1 Fix: MoviePy/Pillow ANTIALIAS compatibility
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import ImageClip, TextClip, AudioFileClip, CompositeVideoClip, ColorClip

# API Keys
PIXABAY_KEY = os.getenv('PIXABAY_API_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_API_KEY')
OPENROUTER_KEY = os.getenv('OPENROUTER_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

AUTHOR = "Lucas Hart"
DURATION = 5  # Aapki requirement: 5 seconds

def get_ai_data():
    """Mistake 2 Fix: AI response cleaning and Error handling"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    prompt = f"Write one short unique motivational quote by {AUTHOR}. Max 45 chars. No stars, no labels. Just the text."
    
    try:
        res = requests.post(url, headers={"Authorization": f"Bearer {OPENROUTER_KEY}"}, 
                            json={"model": "google/gemini-2.0-flash-exp:free", "messages": [{"role": "user", "content": prompt}]}, timeout=20)
        if res.status_code == 200:
            raw_text = res.json()['choices'][0]['message']['content'].strip()
            # Clean Stars, Quotes and Labels
            return raw_text.replace("*", "").replace('"', "").replace("Quote:", "").replace("Title:", "").strip()
    except:
        pass
    return "Rise above the storm and find the sunshine." # Fallback quote

def get_unique_nature_img():
    url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q=nature+landscape&orientation=vertical&per_page=100"
    hits = requests.get(url).json().get('hits', [])
    
    history = []
    if os.path.exists("video_history.txt"):
        with open("video_history.txt", "r") as f: history = f.read().splitlines()

    for hit in hits:
        if str(hit['id']) not in history:
            with open("video_history.txt", "a") as f: f.write(str(hit['id']) + "\n")
            img_data = requests.get(hit['largeImageURL']).content
            with open('bg.jpg', 'wb') as f: f.write(img_data)
            return 'bg.jpg'
    return None

def create_video(quote_text):
    # Background setting
    bg_path = get_unique_nature_img()
    clip = ImageClip(bg_path).set_duration(DURATION).resize(height=1920)
    
    # Mistake 3 Fix: Highlight logic (Shadow box + Big Font)
    shadow = ColorClip(size=(950, 450), color=(0,0,0)).set_opacity(0.5).set_duration(DURATION).set_position('center')
    
    display_text = f"{quote_text}\n\n- {AUTHOR}"
    txt_clip = TextClip(display_text, fontsize=80, color='white', font='Arial-Bold', 
                        method='caption', size=(850, None), align='Center',
                        stroke_color='black', stroke_width=2).set_duration(DURATION).set_position('center')
    
    # Music logic
    m_url = f"https://freesound.org/apiv2/search/text/?query=piano+soft&token={FREESOUND_KEY}"
    s_id = requests.get(m_url).json()['results'][0]['id']
    m_info = requests.get(f"https://freesound.org/apiv2/sounds/{s_id}/?token={FREESOUND_KEY}").json()
    with open('music.mp3', 'wb') as f: f.write(requests.get(m_info['previews']['preview-hq-mp3']).content)
    
    audio = AudioFileClip('music.mp3').subclip(0, DURATION)
    
    # Final Merge
    video = CompositeVideoClip([clip, shadow, txt_clip]).set_audio(audio)
    video.write_videofile("final_short.mp4", fps=24, codec="libx264", audio_codec="aac")
    return "final_short.mp4"

def upload_to_catbox(file):
    with open(file, 'rb') as f:
        res = requests.post("https://catbox.moe/user/api.php", 
                            data={'reqtype': 'fileupload'}, files={'fileToUpload': f})
    return res.text.strip()

# Execution
try:
    content = get_ai_data()
    video_file = create_video(content)
    catbox_url = upload_to_catbox(video_file)

    if "http" in catbox_url:
        # Title limit 50 chars + 8 Hashtags
        caption = f"✨ {content[:48]}\n\n#motivation #lucashart #shorts #nature #quotes #success #inspiration #mindset"
        
        # Telegram send
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", 
                      data={"chat_id": TG_CHAT_ID, "video": catbox_url, "caption": caption}).raise_for_status()
        
        # Webhook send
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"video_url": catbox_url, "caption": caption})
            
        print(f"Success! URL: {catbox_url}")
except Exception as e:
    print(f"Final Error: {e}")
    exit(1)
