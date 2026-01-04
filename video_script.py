import requests, os, random, json, time

# PIL Fix for moviepy compatibility
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import ImageClip, TextClip, AudioFileClip, CompositeVideoClip

# API Keys from GitHub Secrets
PIXABAY_KEY = os.getenv('PIXABAY_API_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_API_KEY')
STRAICO_API_KEY = os.getenv('STRAICO_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

AUTHOR = "Lucas Hart"
DURATION = 5 

def get_ai_data():
    """Straico API integration with JSON cleaning"""
    url = "https://api.straico.com/v1/prompt/completion"
    prompt = (f"Generate a unique motivational quote by {AUTHOR} (max 100 chars) "
              f"and a matching short catchy title (max 40 chars). "
              f"Return ONLY a raw JSON object: {{\"title\": \"...\", \"quote\": \"...\"}}")
    
    headers = {"Authorization": f"Bearer {STRAICO_API_KEY}"}
    payload = {"models": ["google/gemini-2.0-flash-exp"], "message": prompt}
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            raw_content = res.json()['data']['completions']['google/gemini-2.0-flash-exp']['completion'].strip()
            if "```json" in raw_content:
                raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            content = json.loads(raw_content)
            return content['title'], content['quote']
    except Exception as e:
        print(f"AI Error: {e}")
    return "Daily Inspiration", "Your only limit is your mind."

def get_unique_img():
    """FIXED: Clean Pixabay URL without markdown brackets"""
    query = "nature+landscape+forest+mountain+-cgi+-animation+-vector+-artwork"
    # CLEAN URL FIX:
    url = f"[https://pixabay.com/api/?key=](https://pixabay.com/api/?key=){PIXABAY_KEY}&q={query}&image_type=photo&orientation=vertical&per_page=100"
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200: return None
        
        hits = response.json().get('hits', [])
        history_file = "video_history.txt"
        history = open(history_file, "r").read().splitlines() if os.path.exists(history_file) else []
        
        random.shuffle(hits)
        for hit in hits:
            if str(hit['id']) not in history:
                img_data = requests.get(hit['largeImageURL'], timeout=15).content
                if img_data:
                    with open('bg.jpg', 'wb') as f: f.write(img_data)
                    with open(history_file, "a") as f: f.write(str(hit['id']) + "\n")
                    return 'bg.jpg'
    except Exception as e:
        print(f"Image Fetch Error: {e}")
    return None

def create_video(quote_text):
    """Video creation with dark background and white text"""
    bg_path = get_unique_img()
    if not bg_path: raise Exception("Image download fail ho gayi.")
    
    # Image Darkening (No Outline needed)
    bg = ImageClip(bg_path).set_duration(DURATION).resize(height=1920).fl_image(lambda image: (image * 0.7).astype('uint8'))
    
    # Pure White text (No stroke)
    txt = TextClip(f"{quote_text}\n\n- {AUTHOR}", fontsize=65, color='white', font='Arial-Bold', 
                   method='caption', size=(850, None), stroke_width=0).set_duration(DURATION).set_position('center')
    
    final = CompositeVideoClip([bg, txt])
    
    # Piano Music
    try:
        m_res = requests.get(f"[https://freesound.org/apiv2/search/text/?query=piano+soft&token=](https://freesound.org/apiv2/search/text/?query=piano+soft&token=){FREESOUND_KEY}", timeout=10).json()
        s_id = m_res['results'][0]['id']
        m_info = requests.get(f"[https://freesound.org/apiv2/sounds/](https://freesound.org/apiv2/sounds/){s_id}/?token={FREESOUND_KEY}", timeout=10).json()
        with open('music.mp3', 'wb') as f: f.write(requests.get(m_info['previews']['preview-hq-mp3']).content)
        final = final.set_audio(AudioFileClip('music.mp3').subclip(0, DURATION))
    except: pass
    
    final.write_videofile("final_short.mp4", fps=24, codec="libx264", audio_codec="aac")
    return "final_short.mp4"

# --- Main Flow ---
try:
    print("Step 1: AI Data Fetching...")
    title, quote = get_ai_data()
    
    print("Step 2: Video Creation...")
    video_file = create_video(quote)
    
    print("Step 3: Uploading to Catbox...")
    with open(video_file, 'rb') as f:
        catbox_url = requests.post("[https://catbox.moe/user/api.php](https://catbox.moe/user/api.php)", data={'reqtype': 'fileupload'}, files={'fileToUpload': f}).text.strip()
    
    if "http" in catbox_url:
        caption = f"🎬 **{title}**\n\n✨ {quote}\n\n#motivation #nature #shorts #lucashart"
        
        # Telegram Post
        requests.post(f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TG_TOKEN}/sendVideo", 
                      data={"chat_id": TG_CHAT_ID, "video": catbox_url, "caption": caption, "parse_mode": "Markdown"})
        
        # Webhook for Make.com (Using 'url' key for mapping)
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"url": catbox_url, "title": title, "caption": caption}, timeout=10)
            
        print(f"Success! URL: {catbox_url}")
    else:
        print("Catbox Upload Failed.")
except Exception as e:
    print(f"Fatal Error: {e}")
