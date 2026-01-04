import requests, os, random, json
from moviepy.editor import ImageClip, TextClip, AudioFileClip, CompositeVideoClip

# API Keys from GitHub Secrets
PIXABAY_KEY = os.getenv('PIXABAY_API_KEY')
FREESOUND_KEY = os.getenv('FREESOUND_API_KEY')
OPENROUTER_KEY = os.getenv('OPENROUTER_API_KEY')
TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

AUTHOR = "Lucas Hart"

def get_ai_data():
    """Short Quote aur Title lena (Max 40-50 chars)"""
    prompt = f"Write a unique short motivational quote by {AUTHOR} (max 40 chars). Also a short title (max 30 chars) and 8 hashtags."
    res = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
        json={
            "model": "google/gemini-2.0-flash-exp:free",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    return res.json()['choices'][0]['message']['content']

def get_unique_nature_img():
    """Pixabay se nature image lena aur repetition rokna"""
    url = f"https://pixabay.com/api/?key={PIXABAY_KEY}&q=nature+landscape&orientation=vertical&per_page=100"
    hits = requests.get(url).json()['hits']
    
    if os.path.exists("video_history.txt"):
        with open("video_history.txt", "r") as f:
            history = f.read().splitlines()
    else:
        history = []

    for hit in hits:
        if str(hit['id']) not in history:
            with open("video_history.txt", "a") as f:
                f.write(str(hit['id']) + "\n")
            img_data = requests.get(hit['largeImageURL']).content
            with open('bg.jpg', 'wb') as f: f.write(img_data)
            return 'bg.jpg'
    return None

def get_soft_music():
    """Freesound se piano music download karna"""
    search = f"https://freesound.org/apiv2/search/text/?query=piano+soft&token={FREESOUND_KEY}"
    sound_id = requests.get(search).json()['results'][0]['id']
    info = requests.get(f"https://freesound.org/apiv2/sounds/{sound_id}/?token={FREESOUND_KEY}").json()
    file_url = info['previews']['preview-hq-mp3']
    with open('music.mp3', 'wb') as f: f.write(requests.get(file_url).content)
    return 'music.mp3'

def create_video(ai_content):
    # Image setting
    bg_img = get_unique_nature_img()
    clip = ImageClip(bg_img).set_duration(8)
    
    # Text Processing (Quote + Author niche)
    # AI response se quote nikalne ka logic (pehle 50 chars)
    display_text = f"{ai_content.splitlines()[0]}\n\n- {AUTHOR}"
    
    txt_clip = TextClip(display_text, fontsize=45, color='white', font='Arial-Bold', 
                        method='caption', size=(600, None)).set_duration(8).set_position('center')
    
    # Audio merge
    audio = AudioFileClip(get_soft_music()).subclip(0, 8)
    
    # Final Merge
    video = CompositeVideoClip([clip, txt_clip]).set_audio(audio)
    video.write_videofile("final_short.mp4", fps=24, codec="libx264")
    return "final_short.mp4"

def upload_to_catbox(file):
    with open(file, 'rb') as f:
        res = requests.post("https://catbox.moe/user/api.php", 
                            data={'reqtype': 'fileupload'}, files={'fileToUpload': f})
    return res.text.strip()

# Main Execution
try:
    content = get_ai_data()
    video_file = create_video(content)
    catbox_url = upload_to_catbox(video_file)

    # Telegram aur Webhook ko URL bhejna
    msg = f"Title/Quote: {content[:50]}...\nAuthor: {AUTHOR}\nURL: {catbox_url}"
    
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo", 
                  data={"chat_id": TG_CHAT_ID, "video": catbox_url, "caption": content[:100]})
    
    requests.post(WEBHOOK_URL, json={"video_url": catbox_url, "details": content})
    
    print(f"Video Posted: {catbox_url}")
except Exception as e:
    print(f"Error: {e}")
