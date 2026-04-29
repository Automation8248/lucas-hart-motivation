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

# --- 20 DAYS STRICT COOLING LOGIC ---
COOLING_DAYS = 20
COOLING_SECONDS = COOLING_DAYS * 24 * 60 * 60
HISTORY_FILE = "cooling_history.json"

# --- 50+ RANDOM USER AGENTS FOR HUMAN SIMULATION ---
USER_AGENTS = [
    # Windows - Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    # Windows - Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    # Windows - Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    # macOS - Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_6_8) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Safari/605.1.15",
    # macOS - Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_7_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # macOS - Firefox
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13.6; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12.7; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Linux - Chrome / Ubuntu
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # iOS - iPhone Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/121.0.6167.66 Mobile/15E148 Safari/604.1",
    # iPad - Safari
    "Mozilla/5.0 (iPad; CPU OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 16_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15", # iPad Pro mimicking Mac
    # Android - Mobile Chrome
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S928U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.101 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; M2101K6G) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.163 Mobile Safari/537.36",
    # Android - Mobile Firefox
    "Mozilla/5.0 (Android 14; Mobile; rv:122.0) Gecko/122.0 Firefox/122.0",
    "Mozilla/5.0 (Android 13; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0",
    "Mozilla/5.0 (Android 12; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0",
    "Mozilla/5.0 (Android 11; Mobile; rv:119.0) Gecko/119.0 Firefox/119.0",
    # Random Bots/Crawlers (To pretend being a search engine sometimes, helpful for open APIs)
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)"
]

def get_headers():
    return {"User-Agent": random.choice(USER_AGENTS)}

# --- History & Cooling Functions ---
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
    if not os.path.exists(folder_path): 
        print(f"Folder not found: {folder_path}")
        return None
        
    valid_exts = ('.jpg', '.jpeg', '.png') if category == "images" else ('.mp3', '.wav', '.m4a')
    all_files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_exts)]
    
    if not all_files: 
        print(f"No valid files found in {folder_path}")
        return None

    current_time = time.time()
    available_files = []
    
    # Check which files have completed 20 days or are completely new
    for f in all_files:
        last_used_time = history[category].get(f, 0)
        if current_time - last_used_time >= COOLING_SECONDS:
            available_files.append(f)

    if available_files:
        # Pick a random file from available ones
        selected_file = random.choice(available_files)
        # Update the usage time to NOW, locking it for the next 20 days
        history[category][selected_file] = current_time
        print(f"Selected {category}: {selected_file} (Locked for next 20 days)")
        return os.path.join(folder_path, selected_file)
    
    print(f"⚠️ Warning: Saari {category} 20 din ke cooling period me hain!")
    return None

# --- API & Video Logic ---
def get_free_quote_only():
    try:
        res = requests.get("https://zenquotes.io/api/random", headers=get_headers(), timeout=10)
        return res.json()[0]['q']
    except: return "Your only limit is your mind."

def create_video(quote_text, history):
    bg_path = get_file_with_cooling("images", "images", history)
    if not bg_path: 
        raise Exception("Images folder khali hai ya sabhi images abhi 20 din ke cooling me hain. Kuch nayi images add karein!")

    bg = ImageClip(bg_path).set_duration(DURATION).resize(height=1920).fl_image(lambda image: (image * 0.6).astype('uint8'))
    full_display_text = f"\"{quote_text}\"\n\n- {FIXED_AUTHOR}"
    txt = TextClip(full_display_text, fontsize=80, color='white', font='Arial-Bold', 
                   method='caption', size=(850, None)).set_duration(DURATION).set_position('center')
    
    audio_path = get_file_with_cooling("ringtones", "ringtones", history)
    audio = None
    if audio_path:
        try: 
            audio = AudioFileClip(audio_path).subclip(0, DURATION)
        except Exception as e: 
            print(f"Audio Load Error: {e}")
    else:
        print("Bina audio ke video ban rahi hai (Ringtones cooling me hain ya folder khali hai).")
    
    final = CompositeVideoClip([bg, txt])
    if audio: final = final.set_audio(audio)
    
    final.write_videofile("final_short.mp4", fps=24, codec="libx264", audio_codec="aac")
    return "final_short.mp4"

# --- FAST UPLOAD LOGIC WITH 10 SERVERS (Zero Delays) ---
def upload_video_with_fallbacks(video_path):
    filename = os.path.basename(video_path)
    print("🚀 Starting Fast 10-Server Upload...")

    servers = [
        ("Catbox", lambda: requests.post("https://catbox.moe/user/api.php", data={'reqtype': 'fileupload'}, files={'fileToUpload': open(video_path, 'rb')}, headers=get_headers(), timeout=30)),
        ("Litterbox", lambda: requests.post("https://litterbox.catbox.moe/resources/internals/api.php", data={'reqtype': 'fileupload', 'time': '72h'}, files={'fileToUpload': open(video_path, 'rb')}, headers=get_headers(), timeout=30)),
        ("0x0.st", lambda: requests.post("https://0x0.st", files={'file': open(video_path, 'rb')}, headers=get_headers(), timeout=30)),
        ("Transfer.sh", lambda: requests.put(f"https://transfer.sh/{filename}", data=open(video_path, 'rb'), headers=get_headers(), timeout=30)),
        ("Uguu.se", lambda: requests.post("https://uguu.se/upload.php", files={'files[]': open(video_path, 'rb')}, headers=get_headers(), timeout=30)),
        ("Tmpfiles.org", lambda: requests.post("https://tmpfiles.org/api/v1/upload", files={'file': open(video_path, 'rb')}, headers=get_headers(), timeout=30)),
        ("Pomf.lain.la", lambda: requests.post("https://pomf.lain.la/upload.php", files={'files[]': open(video_path, 'rb')}, headers=get_headers(), timeout=30)),
        ("Temp.sh", lambda: requests.put(f"https://temp.sh/{filename}", data=open(video_path, 'rb'), headers=get_headers(), timeout=30)),
        ("Bashupload", lambda: requests.put(f"https://bashupload.com/{filename}", data=open(video_path, 'rb'), headers=get_headers(), timeout=30)),
        ("File.io", lambda: requests.post("https://file.io", files={'file': open(video_path, 'rb')}, headers=get_headers(), timeout=30))
    ]

    for name, req_func in servers:
        print(f"Trying {name}...")
        try:
            r = req_func()
            if r.status_code == 200:
                text = r.text.strip()
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
    # Pehle purani history load karo
    history = load_history()
    
    print("Step 1: Fetching Quote...")
    quote = get_free_quote_only()
    
    print("Step 2: Creating Video...")
    # Is step me history update hogi (naye timestamps ke sath)
    video_file = create_video(quote, history)
    
    # Nayi history file me save karo (Github action isko push kar dega)
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
