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

# Basic Headers (Removed heavy randomizer, kept it simple to avoid blocks)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}

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
        res = requests.get("https://zenquotes.io/api/random", headers=HEADERS, timeout=10)
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

# --- FAST UPLOAD LOGIC WITH 10 SERVERS (Zero Delays) ---
def upload_video_with_fallbacks(video_path):
    filename = os.path.basename(video_path)
    print("🚀 Starting Fast 10-Server Upload...")

    servers = [
        ("Catbox", lambda: requests.post("https://catbox.moe/user/api.php", data={'reqtype': 'fileupload'}, files={'fileToUpload': open(video_path, 'rb')}, headers=HEADERS, timeout=30)),
        ("Litterbox", lambda: requests.post("https://litterbox.catbox.moe/resources/internals/api.php", data={'reqtype': 'fileupload', 'time': '72h'}, files={'fileToUpload': open(video_path, 'rb')}, headers=HEADERS, timeout=30)),
        ("0x0.st", lambda: requests.post("https://0x0.st", files={'file': open(video_path, 'rb')}, headers=HEADERS, timeout=30)),
        ("Transfer.sh", lambda: requests.put(f"https://transfer.sh/{filename}", data=open(video_path, 'rb'), headers=HEADERS, timeout=30)),
        ("Uguu.se", lambda: requests.post("https://uguu.se/upload.php", files={'files[]': open(video_path, 'rb')}, headers=HEADERS, timeout=30)),
        ("Tmpfiles.org", lambda: requests.post("https://tmpfiles.org/api/v1/upload", files={'file': open(video_path, 'rb')}, headers=HEADERS, timeout=30)),
        ("Pomf.lain.la", lambda: requests.post("https://pomf.lain.la/upload.php", files={'files[]': open(video_path, 'rb')}, headers=HEADERS, timeout=30)),
        ("Temp.sh", lambda: requests.put(f"https://temp.sh/{filename}", data=open(video_path, 'rb'), headers=HEADERS, timeout=30)),
        ("Bashupload", lambda: requests.put(f"https://bashupload.com/{filename}", data=open(video_path, 'rb'), headers=HEADERS, timeout=30)),
        ("File.io", lambda: requests.post("https://file.io", files={'file': open(video_path, 'rb')}, headers=HEADERS, timeout=30))
    ]

    for name, req_func in servers:
        print(f"Trying {name}...")
        try:
            r = req_func()
            if r.status_code == 200:
                text = r.text.strip()
                # Parse depending on API response type
                if name in ["Uguu.se", "Pomf.lain.la"] and r.json().get("success"): return r.json()["files"][0]["url"]
                elif name == "Tmpfiles.org" and r.json().get("status") == "success": return r.json()["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")
                elif name == "File.io" and r.json().get("success"): return r.json().get("link")
                elif name == "Bashupload":
                    match = re.search(r'(https?://bashupload\.com/\S+)', text)
                    if match: return match.group(1)
                elif text.startswith("http"): 
                    return text
        except Exception as e:
            print(f"{name} Failed.")
            continue
            
    return None

# --- Main Flow ---
try:
    history = load_history()
    print("Step 1: Fetching Quote...")
    quote = get_free_quote_only()
    
    print("Step 2: Creating Video...")
    video_file = create_video(quote, history)
    save_history(history)
    
    print("Step 3: Uploading...")
    final_url = upload_video_with_fallbacks(video_file)

    if final_url:
        clean_title = f"Motivational Quote by {FIXED_AUTHOR}".replace('*', '')
        clean_quote = quote.replace('*', '') 
        caption = f"🎬 {clean_title}\n\n✨ {clean_quote}\n\n#motivation #lucashart #nature #quotes #shorts"
        
        print("Step 4: Sending Webhook/Telegram...")
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", data={"chat_id": TG_CHAT_ID, "video": final_url, "caption": caption, "parse_mode": "Markdown"})
            print("Telegram send success.")
        except: pass
        
        if WEBHOOK_URL:
            try:
                requests.post(WEBHOOK_URL, json={"url": final_url, "title": clean_title, "caption": caption}, timeout=10)
                print("Webhook send success.")
            except: pass
            
        print(f"Workflow Complete! Link: {final_url}")
    else:
        print("Fatal Error: All 10 upload servers failed.")

except Exception as e:
    print(f"Fatal Error: {e}")
