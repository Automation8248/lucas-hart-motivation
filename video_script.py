import requests, os, random, json, time

# PIL Fix for moviepy compatibility
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import ImageClip, TextClip, AudioFileClip, CompositeVideoClip

# API Keys from GitHub Secrets
PIXABAY_KEY = os.getenv('PIXABAY_API_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_API_KEY')
STRAICO_API_KEY = os.getenv('STRAICO_API_KEY') # OpenRouter ki jagah Straico
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

AUTHOR = "Lucas Hart"
DURATION = 5 

def get_ai_data():
    """Straico API se Title aur Quote lena (JSON Format)"""
    url = "https://api.straico.com/v1/prompt/completion"
    prompt = (f"Generate a unique motivational quote by {AUTHOR} (max 100 chars) "
              f"and a catchy title (max 40 chars). "
              f"Return ONLY a raw JSON object: {{\"title\": \"...\", \"quote\": \"...\"}}")
    
    headers = {"Authorization": f"Bearer {STRAICO_API_KEY}"}
    payload = {"models": ["google/gemini-2.0-flash-exp"], "message": prompt}
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=25)
        raw_content = res.json()['data']['completions']['google/gemini-2.0-flash-exp']['completion'].strip()
        
        # Clean markdown if present
        if "```json" in raw_content:
            raw_content = raw_content.split("```json")[1].split("```")[0].strip()
        
        content = json.loads(raw_content)
        return content['title'], content['quote']
    except:
        return "Daily Inspiration", "Success starts with self-discipline."

def get_unique_nature_img():
    """Clean Pixabay URL logic (Fixed Markdown Brackets issue)"""
    query = "nature+landscape+mountain"
    # CLEAN URL: No brackets or extra links
    pix_url = f"[https://pixabay.com/api/?key=](https://pixabay.com/api/?key=){PIXABAY_KEY}&q={query}&orientation=vertical&per_page=100"
    
    try:
        response = requests.get(pix_url, timeout=15).json()
        hits = response.get('hits', [])
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
        print(f"Pixabay Error: {e}")
    return None

def create_video(quote_text):
    """Video logic: Dark background + Pure White text (No Outline)"""
    bg_img = get_unique_nature_img()
    if not bg_img: raise Exception("Image download failed.")

    # Darken image to make white text pop
    clip = ImageClip(bg_img).set_duration(DURATION).resize(height=1920).fl_image(lambda image: (image * 0.7).astype('uint8'))
    
    # Pure White Text logic
    display_text = f"{quote_text}\n\n- {AUTHOR}"
    txt_clip = TextClip(display_text, fontsize=65, color='white', font='Arial-Bold', 
                        method='caption', size=(850, None), stroke_width=0).set_duration(DURATION).set_position('center')
    
    # Audio setup
    try:
        search = f"[https://freesound.org/apiv2/search/text/?query=piano+soft&token=](https://freesound.org/apiv2/search/text/?query=piano+soft&token=){FREESOUND_KEY}"
        s_id = requests.get(search, timeout=10).json()['results'][0]['id']
        info = requests.get(f"[https://freesound.org/apiv2/sounds/](https://freesound.org/apiv2/sounds/){s_id}/?token={FREESOUND_KEY}", timeout=10).json()
        with open('music.mp3', 'wb') as f: f.write(requests.get(info['previews']['preview-hq-mp3']).content)
        audio = AudioFileClip('music.mp3').subclip(0, DURATION)
    except:
        audio = None
    
    video = CompositeVideoClip([clip, txt_clip])
    if audio: video = video.set_audio(audio)
    
    video.write_videofile("final_short.mp4", fps=24, codec="libx264", audio_codec="aac")
    return "final_short.mp4"

# --- Main Flow ---
try:
    print("Step 1: AI Data...")
    title, quote = get_ai_data()
    
    print("Step 2: Video...")
    video_file = create_video(quote)
    
    print("Step 3: Upload...")
    with open(video_file, 'rb') as f:
        catbox_url = requests.post("[https://catbox.moe/user/api.php](https://catbox.moe/user/api.php)", 
                                    data={'reqtype': 'fileupload'}, files={'fileToUpload': f}).text.strip()
    
    if "http" in catbox_url:
        caption = f"🎬 **{title}**\n\n✨ {quote}\n\n#motivation #nature #shorts #lucashart #inspiration #success #mindset #life"
        
        # Telegram Post
        requests.post(f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TG_TOKEN}/sendVideo", 
                      data={"chat_id": TG_CHAT_ID, "video": catbox_url, "caption": caption, "parse_mode": "Markdown"})
        
        # Webhook for Make.com (Mapping Fixed)
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"url": catbox_url, "title": title, "caption": caption}, timeout=10)
        
        print(f"Success! URL: {catbox_url}")
    else:
        print("Catbox error.")

except Exception as e:
    print(f"Fatal Error: {e}")
