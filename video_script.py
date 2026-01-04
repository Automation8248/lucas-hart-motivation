import requests, os, random, json, time

# PIL Fix for moviepy compatibility
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import ImageClip, TextClip, AudioFileClip, CompositeVideoClip

# API Keys from GitHub Secrets
PIXABAY_KEY = os.getenv('PIXABAY_API_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_API_KEY')
OPENROUTER_KEY = os.getenv('OPENROUTER_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

AUTHOR = "Lucas Hart"
DURATION = 5 

def get_ai_quote():
    """OpenRouter Free version with Fallback for 429 errors"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    prompt = f"Write one unique short motivational sentence by {AUTHOR}. Max 45 characters. No titles, no labels, no stars. Just the text."
    
    try:
        res = requests.post(url, headers={"Authorization": f"Bearer {OPENROUTER_KEY}"}, 
                            json={"model": "google/gemini-2.0-flash-exp:free", "messages": [{"role": "user", "content": prompt}]}, timeout=20)
        if res.status_code == 200:
            quote = res.json()['choices'][0]['message']['content'].strip()
            return quote.replace("*", "").replace('"', "").replace("Quote:", "").strip()
    except:
        pass
    
    fallbacks = ["Your only limit is your mind.", "Dream big, work hard, stay focused.", "Success is a journey, not a destination."]
    return random.choice(fallbacks)

def get_unique_img():
    """Sirf 'Real Nature' images lene ke liye specific search query"""
    # Query mein filters add kiye hain taaki artificial/animation na aaye
    query = "nature+landscape+forest+mountain+-cgi+-animation+-vector+-artwork"
    url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q={query}&image_type=photo&orientation=vertical&per_page=100"
    
    try:
        response = requests.get(url).json()
        hits = response.get('hits', [])
        
        history = []
        if os.path.exists("video_history.txt"):
            with open("video_history.txt", "r") as f: history = f.read().splitlines()

        for hit in hits:
            if str(hit['id']) not in history:
                with open("video_history.txt", "a") as f: f.write(str(hit['id']) + "\n")
                img_data = requests.get(hit['largeImageURL']).content
                with open('bg.jpg', 'wb') as f: f.write(img_data)
                return 'bg.jpg'
    except Exception as e:
        print(f"Image fetch error: {e}")
    return None

def create_video(quote_text):
    # Background Image (Real Nature Only)
    bg_path = get_unique_img()
    if not bg_path:
        raise Exception("Could not fetch a real nature image.")
        
    bg = ImageClip(bg_path).set_duration(DURATION).resize(height=1920)
    
    # Yellow Highlighted Text (No Shadow Box, High Contrast)
    full_text = f"{quote_text}\n\n- {AUTHOR}"
    txt = TextClip(full_text, 
                   fontsize=85, 
                   color='white', 
                   font='Arial-Bold', 
                   method='caption', 
                   size=(850, None), 
                   align='Center', 
                   stroke_color='black', 
                   stroke_width=3).set_duration(DURATION).set_position('center')
    
    # Piano Music Fetch
    try:
        m_res = requests.get(f"https://freesound.org/apiv2/search/text/?query=piano+soft&token={FREESOUND_KEY}")
        s_id = m_res.json()['results'][0]['id']
        m_info = requests.get(f"https://freesound.org/apiv2/sounds/{s_id}/?token={FREESOUND_KEY}").json()
        with open('music.mp3', 'wb') as f: f.write(requests.get(m_info['previews']['preview-hq-mp3']).content)
        audio = AudioFileClip('music.mp3').subclip(0, DURATION)
    except:
        # Simple audio fallback if API fails
        audio = None
    
    # Final Merge
    video = CompositeVideoClip([bg, txt])
    if audio:
        video = video.set_audio(audio)
        
    video.write_videofile("final_short.mp4", fps=24, codec="libx264", audio_codec="aac")
    return "final_short.mp4"

def upload_catbox(file):
    with open(file, 'rb') as f:
        return requests.post("https://catbox.moe/user/api.php", data={'reqtype': 'fileupload'}, files={'fileToUpload': f}).text.strip()

# Main Flow
try:
    print("Fetching Quote...")
    quote = get_ai_quote()
    
    print("Creating Video with Real Nature Image...")
    video_file = create_video(quote)
    
    print("Uploading to Catbox...")
    catbox_url = upload_catbox(video_file)
    
    if "http" in catbox_url:
        # Title/Caption control (Max 50 chars) + 8 Hashtags
        caption = f"✨ {quote[:48]}\n\n#motivation #lucashart #shorts #nature #quotes #success #inspiration #mindset"
        
        print("Sending to Telegram...")
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", 
                      data={"chat_id": TG_CHAT_ID, "video": catbox_url, "caption": caption}).raise_for_status()

        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"video_url": catbox_url, "caption": caption})
        
        print(f"Success! Catbox Link: {catbox_url}")
    else:
        print(f"Catbox Error: {catbox_url}")

except Exception as e:
    print(f"Error: {e}")
    exit(1)
