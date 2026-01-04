import requests, os, random, json, time

# PIL Fix for moviepy compatibility
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import ImageClip, TextClip, AudioFileClip, CompositeVideoClip

# API Keys
PIXABAY_KEY = os.getenv('PIXABAY_API_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_API_KEY')
STRAICO_API_KEY = os.getenv('STRAICO_API_KEY') # OpenRouter ki jagah Straico Use karein
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

AUTHOR = "Lucas Hart"
DURATION = 5 

def get_ai_data():
    """Straico API se Dynamic Title aur Quote generate karein"""
    url = "https://api.straico.com/v1/prompt/completion"
    
    # AI ko strict JSON instruction
    prompt = (f"Generate a unique motivational quote by {AUTHOR} (max 100 chars) "
              f"and a matching short catchy title (max 40 chars). "
              f"Return ONLY a raw JSON object: {{\"title\": \"...\", \"quote\": \"...\"}}")
    
    headers = {"Authorization": f"Bearer {STRAICO_API_KEY}"}
    payload = {
        "models": ["google/gemini-2.0-flash-exp"], # Straico supported model
        "message": prompt
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            # Straico response structure handle karein
            raw_content = res.json()['data']['completions']['google/gemini-2.0-flash-exp']['completion'].strip()
            
            # Cleaning markdown if AI sends it
            if "```json" in raw_content:
                raw_content = raw_content.split("```json")[1].split("```")[0].strip()
            
            content = json.loads(raw_content)
            return content['title'], content['quote']
    except Exception as e:
        print(f"Straico Error: {e}")
    
    return "Daily Inspiration", "Your only limit is your mind."

def get_unique_img():
    query = "nature+landscape+forest+mountain+-cgi+-animation+-vector+-artwork"
    url = f"[https://pixabay.com/api/?key=](https://pixabay.com/api/?key=){PIXABAY_KEY}&q={query}&image_type=photo&orientation=vertical&per_page=100"
    try:
        hits = requests.get(url).json().get('hits', [])
        history = []
        if os.path.exists("video_history.txt"):
            with open("video_history.txt", "r") as f: history = f.read().splitlines()
        for hit in hits:
            if str(hit['id']) not in history:
                with open("video_history.txt", "a") as f: f.write(str(hit['id']) + "\n")
                with open('bg.jpg', 'wb') as f: f.write(requests.get(hit['largeImageURL']).content)
                return 'bg.jpg'
    except: return None

def create_video(quote_text):
    bg_path = get_unique_img()
    # Darken image by 30% to make white text pop (No black outline)
    bg = ImageClip(bg_path).set_duration(DURATION).resize(height=1920).fl_image(lambda image: (image * 0.7).astype('uint8'))
    
    full_text = f"{quote_text}\n\n- {AUTHOR}"
    txt = TextClip(full_text, fontsize=70, color='white', font='Arial-Bold', method='caption', 
                   size=(850, None), align='Center', stroke_width=0).set_duration(DURATION).set_position('center')
    
    # Soft Piano Music
    m_res = requests.get(f"[https://freesound.org/apiv2/search/text/?query=piano+soft&token=](https://freesound.org/apiv2/search/text/?query=piano+soft&token=){FREESOUND_KEY}")
    s_id = m_res.json()['results'][0]['id']
    m_info = requests.get(f"[https://freesound.org/apiv2/sounds/](https://freesound.org/apiv2/sounds/){s_id}/?token={FREESOUND_KEY}").json()
    with open('music.mp3', 'wb') as f: f.write(requests.get(m_info['previews']['preview-hq-mp3']).content)
    
    final = CompositeVideoClip([bg, txt]).set_audio(AudioFileClip('music.mp3').subclip(0, DURATION))
    final.write_videofile("final_short.mp4", fps=24, codec="libx264", audio_codec="aac")
    return "final_short.mp4"

# --- Main Flow ---
try:
    print("Step 1: Fetching Straico AI Data...")
    title, quote = get_ai_data()
    
    print("Step 2: Creating Video...")
    video_file = create_video(quote)
    
    print("Step 3: Uploading to Catbox...")
    with open(video_file, 'rb') as f:
        catbox_url = requests.post("[https://catbox.moe/user/api.php](https://catbox.moe/user/api.php)", data={'reqtype': 'fileupload'}, files={'fileToUpload': f}).text.strip()
    
    if "http" in catbox_url:
        # Dynamic Caption with 8 hashtags
        caption = f"🎬 **{title}**\n\n✨ {quote}\n\n#motivation #lucashart #shorts #nature #quotes #success #inspiration #mindset"
        
        print("Step 4: Sending to Telegram & Webhook...")
        # Telegram Post
        requests.post(f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TG_TOKEN}/sendVideo", 
                      data={"chat_id": TG_CHAT_ID, "video": catbox_url, "caption": caption, "parse_mode": "Markdown"})
        
        # Webhook Post (Structured specifically for Make.com mapping)
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={
                "url": catbox_url, 
                "title": title, 
                "caption": caption
            }, timeout=10)
            
        print(f"Success! Video URL: {catbox_url}")
    else:
        print("Upload Failed.")

except Exception as e:
    print(f"Fatal Error: {e}")
    exit(1)
