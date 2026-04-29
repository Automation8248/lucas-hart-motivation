import requests, os, random, json, time, re
import PIL.Image

# PIL Fix for moviepy compatibility
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import ImageClip, TextClip, AudioFileClip, CompositeVideoClip

# Config & Keys
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Fixed Author Name & Settings
FIXED_AUTHOR = "Lucas Hart"
DURATION = 5
COOLING_DAYS = 6
COOLING_SECONDS = COOLING_DAYS * 24 * 60 * 60
HISTORY_FILE = "cooling_history.json"

# --- Human Behavior Simulation Logic ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15"
]

def human_delay():
    time.sleep(random.uniform(2.5, 4.8))

def get_headers():
    return {"User-Agent": random.choice(USER_AGENTS)}

# --- History & Cooling Logic ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {"images": {}, "ringtones": {}}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def get_file_with_cooling(folder_path, category, history):
    if not os.path.exists(folder_path): return None
    
    valid_exts = ('.jpg', '.jpeg', '.png') if category == "images" else ('.mp3', '.wav', '.m4a')
    all_files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_exts)]
    
    if not all_files: return None

    current_time = time.time()
    available_files = [f for f in all_files if current_time - history[category].get(f, 0) >= COOLING_SECONDS]

    if available_files:
        selected_file = random.choice(available_files)
        history[category][selected_file] = current_time
        return os.path.join(folder_path, selected_file)
    return None

# --- API & Video Logic ---
def get_free_quote_only():
    try:
        human_delay()
        res = requests.get("https://zenquotes.io/api/random", headers=get_headers(), timeout=15)
        return res.json()[0]['q']
    except: return "Your only limit is your mind."

def create_video(quote_text, history):
    bg_path = get_file_with_cooling("images", "images", history)
    if not bg_path: raise Exception("Images folder empty hai ya saari images 6 din ki cooling me hain.")

    bg = ImageClip(bg_path).set_duration(DURATION).resize(height=1920).fl_image(lambda image: (image * 0.6).astype('uint8'))
    full_display_text = f"\"{quote_text}\"\n\n- {FIXED_AUTHOR}"
    txt = TextClip(full_display_text, fontsize=80, color='white', font='Arial-Bold', 
                   method='caption', size=(850, None)).set_duration(DURATION).set_position('center')
    
    audio_path = get_file_with_cooling("ringtones", "ringtones", history)
    audio = None
    if audio_path:
        try: audio = AudioFileClip(audio_path).subclip(0, DURATION)
        except Exception as e: print(f"Audio Load Error: {e}")
    
    final = CompositeVideoClip([bg, txt])
    if audio: final = final.set_audio(audio)
    
    final.write_videofile("final_short.mp4", fps=24, codec="libx264", audio_codec="aac")
    return "final_short.mp4"

def upload_video_with_fallbacks(video_path):
    headers = get_headers()
    filename = os.path.basename(video_path)
    
    print("🚀 Starting 10-Server Upload Fallback Process...")

    # 1. Catbox.moe
    print("1. Trying Catbox...")
    for attempt in range(2):
        human_delay()
        try:
            with open(video_path, 'rb') as f:
                r = requests.post("https://catbox.moe/user/api.php", data={'reqtype': 'fileupload'}, files={'fileToUpload': f}, headers=headers, timeout=60)
                if r.status_code == 200 and r.text.strip().startswith("http"): 
                    return r.text.strip()
        except Exception as e: print(f"Catbox failed: {e}")

    # 2. Litterbox (Litbox)
    print("2. Trying Litterbox...")
    human_delay()
    try:
        with open(video_path, 'rb') as f:
            r = requests.post("https://litterbox.catbox.moe/resources/internals/api.php", data={'reqtype': 'fileupload', 'time': '72h'}, files={'fileToUpload': f}, headers=headers, timeout=60)
            if r.status_code == 200 and r.text.strip().startswith("http"): 
                return r.text.strip()
    except Exception as e: print(f"Litterbox failed: {e}")

    # 3. 0x0.st
    print("3. Trying 0x0.st...")
    human_delay()
    try:
        with open(video_path, 'rb') as f:
            r = requests.post("https://0x0.st", files={'file': f}, headers=headers, timeout=60)
            if r.status_code == 200 and r.text.strip().startswith("http"):
                return r.text.strip()
    except Exception as e: print(f"0x0.st failed: {e}")

    # 4. Transfer.sh
    print("4. Trying Transfer.sh...")
    human_delay()
    try:
        with open(video_path, 'rb') as f:
            r = requests.put(f"https://transfer.sh/{filename}", data=f, headers=headers, timeout=60)
            if r.status_code == 200 and r.text.strip().startswith("http"):
                return r.text.strip()
    except Exception as e: print(f"Transfer.sh failed: {e}")

    # 5. Uguu.se
    print("5. Trying Uguu.se...")
    human_delay()
    try:
        with open(video_path, 'rb') as f:
            r = requests.post("https://uguu.se/upload.php", files={'files[]': f}, headers=headers, timeout=60)
            if r.status_code == 200:
                data = r.json()
                if data.get("success"): return data["files"][0]["url"]
    except Exception as e: print(f"Uguu.se failed: {e}")

    # 6. Tmpfiles.org
    print("6. Trying Tmpfiles.org...")
    human_delay()
    try:
        with open(video_path, 'rb') as f:
            r = requests.post("https://tmpfiles.org/api/v1/upload", files={'file': f}, headers=headers, timeout=60)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "success":
                    return data["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")
    except Exception as e: print(f"Tmpfiles.org failed: {e}")

    # 7. Pomf.lain.la
    print("7. Trying Pomf.lain.la...")
    human_delay()
    try:
        with open(video_path, 'rb') as f:
            r = requests.post("https://pomf.lain.la/upload.php", files={'files[]': f}, headers=headers, timeout=60)
            if r.status_code == 200:
                data = r.json()
                if data.get("success"): return data["files"][0]["url"]
    except Exception as e: print(f"Pomf.lain.la failed: {e}")

    # 8. temp.sh
    print("8. Trying Temp.sh...")
    human_delay()
    try:
        with open(video_path, 'rb') as f:
            r = requests.put(f"https://temp.sh/{filename}", data=f, headers=headers, timeout=60)
            if r.status_code == 200 and r.text.strip().startswith("http"):
                return r.text.strip()
    except Exception as e: print(f"Temp.sh failed: {e}")

    # 9. Bashupload.com
    print("9. Trying Bashupload...")
    human_delay()
    try:
        with open(video_path, 'rb') as f:
            r = requests.put(f"https://bashupload.com/{filename}", data=f, headers=headers, timeout=60)
            if r.status_code == 200:
                match = re.search(r'(https?://bashupload\.com/\S+)', r.text)
                if match: return match.group(1)
    except Exception as e: print(f"Bashupload failed: {e}")

    # 10. File.io (Last Resort)
    print("10. Trying File.io...")
    human_delay()
    try:
        with open(video_path, 'rb') as f:
            r = requests.post("https://file.io", files={'file': f}, headers=headers, timeout=60)
            if r.status_code == 200:
                data = r.json()
                if data.get("success"): return data.get("link")
    except Exception as e: print(f"File.io failed: {e}")
    
    return None

# --- Main Flow ---
try:
    history = load_history()
    
    print("Step 1: Fetching Quote...")
    quote = get_free_quote_only()
    
    print("Step 2: Creating Video with 6-Days Cooling & Human Logic...")
    video_file = create_video(quote, history)
    
    # Save history
    save_history(history)
    
    print("Step 3: Multi-Server Upload Process...")
    final_url = upload_video_with_fallbacks(video_file)

    if final_url:
        raw_title = f"Motivational Quote by {FIXED_AUTHOR}"
        clean_quote = quote.replace('*', '') 
        clean_title = raw_title.replace('*', '')
        
        caption = f"🎬 {clean_title}\n\n✨ {clean_quote}\n\n#motivation #lucashart #nature #quotes #shorts"
        
        print("Step 4: Sending to Telegram & Webhook...")
        human_delay()
        
        # Telegram Post
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", 
                          data={"chat_id": TG_CHAT_ID, "video": final_url, "caption": caption, "parse_mode": "Markdown"})
            print("Telegram send success.")
        except Exception as tg_err: print(f"Telegram Failed: {tg_err}")
        
        # Webhook for Make.com
        if WEBHOOK_URL:
            try:
                requests.post(WEBHOOK_URL, json={"url": final_url, "title": clean_title, "caption": caption}, timeout=20)
                print("Webhook send success.")
            except Exception as web_err: print(f"Webhook Failed: {web_err}")
            
        print(f"Workflow Complete! Link: {final_url}")
    else:
        print("Fatal Error: All 10 upload servers failed.")

except Exception as e:
    print(f"Fatal Error: {e}")
