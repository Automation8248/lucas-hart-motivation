import requests, os, random, json, time
import PIL.Image

# PIL Fix for moviepy compatibility
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import ImageClip, TextClip, AudioFileClip, CompositeVideoClip

# Config & Keys
PIXABAY_KEY = os.getenv('PIXABAY_API_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Fixed Author Name
FIXED_AUTHOR = "Lucas Hart"
DURATION = 5

def get_free_quote_only():
    """ZenQuotes API se sirf motivational quote pick karega"""
    try:
        res = requests.get("https://zenquotes.io/api/random", timeout=15)
        data = res.json()[0]
        return data['q']
    except Exception as e:
        print(f"Quote Fetch Error: {e}")
        return "Your only limit is your mind."

def get_real_nature_img():
    """Pixabay se Real Nature photo (No CGI/Animation)"""
    query = "nature+landscape+forest+mountain+-cgi+-animation+-vector"
    url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={query}&image_type=photo&orientation=vertical&per_page=50"
    
    # Retry logic for Pixabay
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=20).json()
            hits = response.get('hits', [])
            history_file = "video_history.txt"
            history = open(history_file, "r").read().splitlines() if os.path.exists(history_file) else []
            
            random.shuffle(hits)
            for hit in hits:
                if str(hit['id']) not in history:
                    img_data = requests.get(hit['largeImageURL'], timeout=20).content
                    if img_data:
                        with open('bg.jpg', 'wb') as f: f.write(img_data)
                        with open(history_file, "a") as f: f.write(str(hit['id']) + "\n")
                        return 'bg.jpg'
        except Exception as e:
            print(f"Image attempt {attempt+1} failed: {e}")
            time.sleep(2)
    return None

def create_video(quote_text):
    """Video banayega: Quote + Fixed Author (Lucas Hart)"""
    bg_path = get_real_nature_img()
    if not bg_path: raise Exception("Image download fail ho gayi sabhi koshishon ke baad.")

    # 1. Background
    bg = ImageClip(bg_path).set_duration(DURATION).resize(height=1920).fl_image(lambda image: (image * 0.6).astype('uint8'))
    
    # 2. Text (Pure White, No Stroke, Fixed Author Lucas Hart)
    full_display_text = f"\"{quote_text}\"\n\n- {FIXED_AUTHOR}"
    
    txt = TextClip(full_display_text, fontsize=80, color='white', font='Arial-Bold', 
                   method='caption', size=(850, None), stroke_width=0).set_duration(DURATION).set_position('center')
    
    # 3. Audio (Piano Music)
    try:
        search = f"https://freesound.org/apiv2/search/text/?query=piano+soft&token={FREESOUND_KEY}"
        s_id = requests.get(search, timeout=15).json()['results'][0]['id']
        info = requests.get(f"https://freesound.org/apiv2/sounds/{s_id}/?token={FREESOUND_KEY}", timeout=15).json()
        with open('music.mp3', 'wb') as f: f.write(requests.get(info['previews']['preview-hq-mp3'], timeout=20).content)
        audio = AudioFileClip('music.mp3').subclip(0, DURATION)
    except: audio = None
    
    final = CompositeVideoClip([bg, txt])
    if audio: final = final.set_audio(audio)
    
    final.write_videofile("final_short.mp4", fps=24, codec="libx264", audio_codec="aac")
    return "final_short.mp4"

# --- Main Flow ---
try:
    print(f"Step 1: Fetching Quote for {FIXED_AUTHOR}...")
    quote = get_free_quote_only()
    
    print("Step 2: Creating Video...")
    video_file = create_video(quote)
    
    print("Step 3: Uploading to Catbox (Fixing Timeout issue)...")
    catbox_url = ""
    # Catbox Retry Logic for your Screenshot error
    for attempt in range(5):
        try:
            with open(video_file, 'rb') as f:
                res = requests.post("https://catbox.moe/user/api.php", 
                                    data={'reqtype': 'fileupload'}, 
                                    files={'fileToUpload': f}, 
                                    timeout=60) # Increased timeout
                catbox_url = res.text.strip()
                if "http" in catbox_url: break
        except Exception as upload_err:
            print(f"Upload attempt {attempt+1} failed: {upload_err}")
            time.sleep(5)
    
    if "http" in catbox_url:
        raw_title = f"Motivational Quote by {FIXED_AUTHOR}"
        clean_quote = quote.replace('*', '').replace('#', '')
        clean_title = raw_title.replace('*', '').replace('#', '')
        caption = f"🎬 {clean_title}\n\n✨ {clean_quote}\n\n#motivation #lucashart #nature #quotes #shorts"
        
        print("Step 4: Sending to Telegram & Webhook...")
        
        # Telegram Post
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", 
                          data={"chat_id": TG_CHAT_ID, "video": catbox_url, "caption": caption, "parse_mode": "Markdown"},
                          timeout=30)
            print("Telegram send success.")
        except Exception as tg_err:
            print(f"Telegram Failed: {tg_err}")

        # Webhook for Make.com
        if WEBHOOK_URL:
            try:
                requests.post(WEBHOOK_URL, json={"url": catbox_url, "title": clean_title, "caption": caption}, timeout=20)
                print("Webhook send success.")
            except Exception as web_err:
                print(f"Webhook Failed: {web_err}")

        print(f"Workflow Complete! Link: {catbox_url}")
    else:
        print("Fatal Error: Catbox upload failed after all attempts.")

except Exception as e:
    print(f"Fatal Error: {e}")
