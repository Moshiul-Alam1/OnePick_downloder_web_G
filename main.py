from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp
import requests

app = FastAPI()

# ==============================================================================
# 1. CORS Middleware
# ==============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

@app.get("/")
def home():
    return {"status": "online", "message": "OnePick Universal Extraction Engine Online!"}

# ==============================================================================
# 2. Cobalt API Fallback Integration (For YouTube 100% Bypass)
# ==============================================================================
def fetch_via_cobalt(video_url: str):
    """
    Cobalt Engine API ব্যবহার করে ইউটিউবের বোট-ডিটেকশন বাইপাস করে
    সরাসরি ডাউনলোডেবল স্ট্রিমিং ইউআরএল বের করে আনার ফাংশন।
    """
    cobalt_endpoint = "https://api.cobalt.tools/"
    payload = {
        "url": video_url,
        "videoQuality": "max"
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(cobalt_endpoint, json=payload, headers=headers, timeout=12)
        if response.status_code == 200:
            data = response.json()
            download_url = data.get("url")
            
            if download_url:
                return {
                    "success": True,
                    "title": "YouTube Video (OnePick Engine)",
                    "thumbnail": "https://img.youtube.com/vi/" + extract_yt_id(video_url) + "/hqdefault.jpg",
                    "duration": 0,
                    "videos": [
                        {
                            "resolution": "HD / Best Quality",
                            "height": 1080,
                            "ext": "mp4",
                            "url": download_url
                        }
                    ],
                    "audio_tracks": []
                }
    except Exception as err:
        print("Cobalt Fetch Failed:", err)
    return None

def extract_yt_id(url: str):
    """ইউটিউব ভিডিও ইউআরএল থেকে ভিডিও আইডি এক্সট্র্যাক্ট করা (থাম্বনেইলের জন্য)"""
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    elif "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "shorts/" in url:
        return url.split("shorts/")[1].split("?")[0]
    return ""

# ==============================================================================
# 3. Main Extraction Logic (Hybrid Engine)
# ==============================================================================
def process_video_extraction(video_url: str):
    is_youtube = "youtube.com" in video_url.lower() or "youtu.be" in video_url.lower()

    # ১. ইউটিউব ভিডিও হলে সরাসরি Cobalt API Engine ট্রাই করা হবে
    if is_youtube:
        cobalt_result = fetch_via_cobalt(video_url)
        if cobalt_result:
            return cobalt_result

    # ২. অন্যান্য প্ল্যাটফর্ম (Facebook, TikTok ইত্যাদি) বা Cobalt ব্যর্থ হলে yt-dlp কাজ করবে
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'skip_download': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['android_vr', 'ios', 'mweb']
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

            videos_list = []
            audio_list = []

            for f in info.get('formats', []):
                stream_url = f.get('url')
                if not stream_url:
                    continue

                res = f.get('resolution') or f"{f.get('width', '')}x{f.get('height', '')}"
                if res == 'x' or not res:
                    res = f.get('format_note', 'Standard')

                ext = f.get('ext', 'mp4')
                vcodec = f.get('vcodec', 'none')
                acodec = f.get('acodec', 'none')

                if vcodec != 'none':
                    videos_list.append({
                        'resolution': res,
                        'height': f.get('height', 0),
                        'ext': ext,
                        'url': stream_url
                    })
                elif acodec != 'none':
                    audio_list.append({
                        'language': f.get('format_note', 'Audio Track'),
                        'bitrate': f"{int(f.get('tbr', 0))} kbps" if f.get('tbr') else "128 kbps",
                        'ext': ext,
                        'url': stream_url
                    })

            if not videos_list and info.get('url'):
                videos_list.append({
                    'resolution': 'Download Video',
                    'height': 0,
                    'ext': info.get('ext', 'mp4'),
                    'url': info.get('url')
                })

            return {
                "success": True,
                "title": info.get('title', 'Media File'),
                "thumbnail": info.get('thumbnail', ''),
                "duration": info.get('duration', 0),
                "videos": videos_list[:12],
                "audio_tracks": audio_list[:5]
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==============================================================================
# 4. API Endpoints
# ==============================================================================
@app.get("/api/extract")
@app.get("/api/fetch")
def extract_get(url: str = Query(..., description="Target Media URL")):
    video_url = url.strip()
    if not video_url:
        raise HTTPException(status_code=400, detail="Please provide a valid URL")
    return process_video_extraction(video_url)

@app.post("/fetch")
@app.post("/api/fetch")
@app.post("/api/extract")
def extract_post(data: VideoRequest):
    video_url = data.url.strip()
    if not video_url:
        raise HTTPException(status_code=400, detail="Please provide a valid URL")
    return process_video_extraction(video_url)
