import requests, os, random, json, time
import PIL.Image

# PIL Fix for moviepy compatibility
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import ImageClip, TextClip, AudioFileClip, CompositeVideoClip

# Config & Keys (Removed Pixabay & Freesound)
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Fixed Author Name & Settings
FIXED_AUTHOR = "Lucas Hart"
DURATION = 5
COOLING_DAYS = 6
COOLING_SECONDS = COOLING_DAYS * 24 * 60 * 60
HISTORY_FILE = "cooling_history.json"

def load_history():
    """History file load karega jismein files ka last used time save hoga"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"images": {}, "ringtones": {}}

def save_history(history):
    """Updated history ko JSON me save karega"""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def get_file_with_cooling(folder_path, category, history):
    """Folder se random file select karega jiska 6 din ka cooling period pura ho chuka ho"""
    if not os.path.exists(folder_path):
        print(f"Error: '{folder_path}' folder nahi mila.")
        return None
    
    all_files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    if not all_files:
        return None

    current_time = time.time()
    available_files = []

    for file in all_files:
        last_used = history[category].get(file, 0)
        # Agar current time aur last used ke beech ka gap 6 din se zyada hai, tabhi select karo
        if current_time - last_used >= COOLING_SECONDS:
            available_files.append(file)

    if available_files:
        selected_file = random.choice(available_files)
        # Update history with current timestamp
        history[category][selected_file] = current_time
        return os.path.join(folder_path, selected_file)
    else:
        return None # Sabhi files currently 6 din ke cooling period mein hain

def get_free_quote_only():
    """ZenQuotes API se sirf motivational quote pick karega"""
    try:
        res = requests.get("https://zenquotes.io/api/random", timeout=15)
        data = res.json()[0]
        return data['q']
    except Exception as e:
        print(f"Quote Fetch Error: {e}")
        return "Your only limit is your mind."

def create_video(quote_text, history):
    """Video banayega: Quote + Fixed Author (Lucas Hart) with cooling logic"""
    bg_path = get_file_with_cooling("images", "images", history)
    if not bg_path: 
        raise Exception("Images folder khali hai ya folder ki sabhi images 6 din ke cooling period mein hain.")

    # 1. Background
    bg = ImageClip(bg_path).set_duration(DURATION).resize(height=1920).fl_image(lambda image: (image * 0.6).astype('uint8'))
    
    # 2. Text (Pure White, No Stroke, Fixed Author Lucas Hart)
    full_display_text = f"\"{quote_text}\"\n\n- {FIXED_AUTHOR}"
    
    txt = TextClip(full_display_text, fontsize=80, color='white', font='Arial-Bold', 
                   method='caption', size=(850, None), stroke_width=0).set_duration(DURATION).set_position('center')
    
    # 3. Audio (Local Ringtones Folder with 6-day cooling check)
    audio_path = get_file_with_cooling("ringtones", "ringtones", history)
    if audio_path:
        try:
            audio = AudioFileClip(audio_path).subclip(0, DURATION)
        except Exception as e:
            print(f"Audio Load Error: {e}")
            audio = None
    else:
        print("Warning: Ringtones folder khali hai ya sabhi audio 6 din ke cooling period mein hain. Bina audio ke proceed kar rahe hain.")
        audio = None
    
    final = CompositeVideoClip([bg, txt])
    if audio: final = final.set_audio(audio)
    
    final.write_videofile("final_short.mp4", fps=24, codec="libx264", audio_codec="aac")
    return "final_short.mp4"

# --- Main Flow ---
try:
    # History load karo
    history = load_history()
    
    print(f"Step 1: Fetching Quote for {FIXED_AUTHOR}...")
    quote = get_free_quote_only()
    
    print("Step 2: Creating Video with 6-Days Cooling Logic...")
    video_file = create_video(quote, history)
    
    # Video successfully banne ke baad history ko save karo taaki next time repeat na ho
    save_history(history)
    
    print("Step 3: Uploading to Catbox (Fixing Timeout issue)...")
    catbox_url = ""
    # Catbox Retry Logic for Screenshot errors
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
        
        # Clean caption format (no hash tags, no formatting symbols)
        caption = f"🎬 {clean_title}\n\n✨ {clean_quote}\n\nmotivation lucashart nature quotes shorts"
        
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
