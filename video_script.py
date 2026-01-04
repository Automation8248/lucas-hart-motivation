import requests, os, random, json, time
from moviepy.editor import ImageClip, TextClip, AudioFileClip, CompositeVideoClip, ColorClip

# API Keys
PIXABAY_KEY = os.getenv('PIXABAY_API_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_API_KEY')
OPENROUTER_KEY = os.getenv('OPENROUTER_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

AUTHOR = "Lucas Hart"
DURATION = 5 

def get_ai_quote():
    """AI se quote lena aur 429 error handle karna"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    prompt = f"Write one short motivational sentence by {AUTHOR}. No titles, no labels, no stars. Just the text. Max 45 characters."
    
    for i in range(3): # 3 baar retry karega agar 429 error aaye
        try:
            res = requests.post(url, headers={"Authorization": f"Bearer {OPENROUTER_KEY}"}, 
                                json={"model": "google/gemini-2.0-flash-exp:free", "messages": [{"role": "user", "content": prompt}]}, timeout=20)
            if res.status_code == 429:
                print("Limit reached, waiting 30 seconds...")
                time.sleep(30)
                continue
            res.raise_for_status()
            quote = res.json()['choices'][0]['message']['content'].strip()
            # Clean Stars and extra labels
            return quote.replace("*", "").replace('"', "").replace("Quote:", "").strip()
        except Exception as e:
            print(f"Attempt {i+1} failed: {e}")
            time.sleep(5)
    
    return "Believe in your journey today." # Fallback quote agar AI fail ho jaye

def create_video(quote_text):
    # Nature Image
    img_res = requests.get(f"https://pixabay.com/api/?key={PIXABAY_KEY}&q=nature+landscape&orientation=vertical&per_page=50")
    img_url = random.choice(img_res.json()['hits'])['largeImageURL']
    with open('bg.jpg', 'wb') as f: f.write(requests.get(img_url).content)
    
    bg = ImageClip('bg.jpg').set_duration(DURATION).resize(height=1920)
    
    # Text Highlighting: Black shadow box piche add karna
    shadow = ColorClip(size=(950, 450), color=(0,0,0)).set_opacity(0.5).set_duration(DURATION).set_position('center')
    
    # Big Font Style
    full_text = f"{quote_text}\n\n- {AUTHOR}"
    txt = TextClip(full_text, fontsize=80, color='white', font='Arial-Bold', method='caption', 
                   size=(850, None), align='Center', stroke_color='black', stroke_width=2).set_duration(DURATION).set_position('center')
    
    # Music
    m_res = requests.get(f"https://freesound.org/apiv2/search/text/?query=piano+soft&token={FREESOUND_KEY}")
    s_id = m_res.json()['results'][0]['id']
    m_info = requests.get(f"https://freesound.org/apiv2/sounds/{s_id}/?token={FREESOUND_KEY}").json()
    with open('music.mp3', 'wb') as f: f.write(requests.get(m_info['previews']['preview-hq-mp3']).content)
    
    final = CompositeVideoClip([bg, shadow, txt]).set_audio(AudioFileClip('music.mp3').subclip(0, DURATION))
    final.write_videofile("short.mp4", fps=24, codec="libx264", audio_codec="aac")
    return "short.mp4"

def upload_catbox(file):
    with open(file, 'rb') as f:
        return requests.post("https://catbox.moe/user/api.php", data={'reqtype': 'fileupload'}, files={'fileToUpload': f}).text.strip()

# Start Process
try:
    print("Fetching Quote...")
    quote = get_ai_quote()
    print(f"Quote: {quote}")
    
    video_file = create_video(quote)
    print("Uploading to Catbox...")
    catbox_url = upload_catbox(video_file)
    
    if "http" in catbox_url:
        caption = f"✨ {quote[:50]}\n\n#motivation #lucashart #shorts #nature"
        
        # Telegram send
        tg_res = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", 
                               data={"chat_id": TG_CHAT_ID, "video": catbox_url, "caption": caption})
        print(f"Telegram Result: {tg_res.status_code}")
        
        # Webhook send
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"video_url": catbox_url, "caption": caption})
    else:
        print("Catbox Upload Failed!")
except Exception as e:
    print(f"Final Error: {e}")
