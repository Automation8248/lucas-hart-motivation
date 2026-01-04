import requests, os, random, json, time
from moviepy.editor import ImageClip, TextClip, AudioFileClip, CompositeVideoClip, ColorClip

# Fetching API Keys
PIXABAY_KEY = os.getenv('PIXABAY_API_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_API_KEY')
OPENROUTER_KEY = os.getenv('OPENROUTER_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

AUTHOR = "Lucas Hart"
DURATION = 5 

def get_ai_quote():
    """OpenRouter Free version with 429 Error Handling"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    prompt = f"Write one short motivational sentence by {AUTHOR}. Max 45 characters. No titles, no labels, no stars. Just the text."
    
    for attempt in range(3):
        try:
            res = requests.post(url, headers={"Authorization": f"Bearer {OPENROUTER_KEY}"}, 
                                json={"model": "google/gemini-2.0-flash-exp:free", "messages": [{"role": "user", "content": prompt}]}, timeout=25)
            if res.status_code == 429:
                print(f"Rate Limit (429). Retrying in 30s (Attempt {attempt+1})...")
                time.sleep(30)
                continue
            res.raise_for_status()
            quote = res.json()['choices'][0]['message']['content'].strip()
            return quote.replace("*", "").replace('"', "").replace("Quote:", "").strip()
        except Exception as e:
            print(f"Error fetching quote: {e}")
            time.sleep(5)
    return "Your only limit is your mind." # Fallback quote

def create_video(quote_text):
    # Pixabay Image
    img_res = requests.get(f"https://pixabay.com/api/?key={PIXABAY_KEY}&q=nature+landscape&orientation=vertical&per_page=50")
    img_url = random.choice(img_res.json()['hits'])['largeImageURL']
    with open('bg.jpg', 'wb') as f: f.write(requests.get(img_url).content)
    
    bg = ImageClip('bg.jpg').set_duration(DURATION).resize(height=1920)
    
    # Shadow Box for Highlighting
    shadow = ColorClip(size=(950, 480), color=(0,0,0)).set_opacity(0.55).set_duration(DURATION).set_position('center')
    
    # Big Highlighted Text
    full_text = f"{quote_text}\n\n- {AUTHOR}"
    txt = TextClip(full_text, fontsize=80, color='white', font='Arial-Bold', method='caption', 
                   size=(850, None), align='Center', stroke_color='black', stroke_width=2).set_duration(DURATION).set_position('center')
    
    # Freesound Piano Music
    m_res = requests.get(f"https://freesound.org/apiv2/search/text/?query=piano+soft&token={FREESOUND_KEY}")
    s_id = m_res.json()['results'][0]['id']
    m_info = requests.get(f"https://freesound.org/apiv2/sounds/{s_id}/?token={FREESOUND_KEY}").json()
    with open('music.mp3', 'wb') as f: f.write(requests.get(m_info['previews']['preview-hq-mp3']).content)
    
    final = CompositeVideoClip([bg, shadow, txt]).set_audio(AudioFileClip('music.mp3').subclip(0, DURATION))
    final.write_videofile("short.mp4", fps=24, codec="libx264", audio_codec="aac")
    return "short.mp4"

# Process Execution
try:
    print("--- Step 1: Fetching AI Quote ---")
    quote = get_ai_quote()
    print(f"Quote: {quote}")
    
    print("--- Step 2: Creating Video ---")
    video_file = create_video(quote)
    
    print("--- Step 3: Uploading to Catbox ---")
    with open(video_file, 'rb') as f:
        catbox_url = requests.post("https://catbox.moe/user/api.php", data={'reqtype': 'fileupload'}, files={'fileToUpload': f}).text.strip()
    
    if "http" not in catbox_url:
        raise Exception(f"Catbox Upload Failed! Response: {catbox_url}")
    print(f"Video URL: {catbox_url}")

    # Caption with 8 hashtags and 50 char limit for title
    short_title = quote[:50]
    caption = f"✨ {short_title}\n\n#motivation #lucashart #shorts #nature #quotes #success #inspiration #mindset"

    print("--- Step 4: Sending to Telegram ---")
    tg_res = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", 
                           data={"chat_id": TG_CHAT_ID, "video": catbox_url, "caption": caption})
    print(f"TG Result: {tg_res.status_code}")
    tg_res.raise_for_status() # If this fails, workflow will fail

    print("--- Step 5: Sending to Webhook ---")
    if WEBHOOK_URL:
        wh_res = requests.post(WEBHOOK_URL, json={"video_url": catbox_url, "caption": caption})
        print(f"Webhook Result: {wh_res.status_code}")
        wh_res.raise_for_status()

    print("Process Finished Successfully!")

except Exception as e:
    print(f"FATAL ERROR: {e}")
    exit(1) # Mark Action as failed
