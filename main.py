import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

# ==============================================================================
# 1. CORS Middleware (Vercel Frontend Cross-Origin Allow করার জন্য)
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

# Render Environment Variable থেকে প্রক্সি ইউআরএল রিড করা
PROXY_URL = os.getenv("PROXY_URL", "http://iatrfknf:xwq173uvyb3j@p.webshare.io:80").strip()

# ==============================================================================
# 2. Root Status Endpoint
# ==============================================================================
@app.get("/")
def home():
    return {
        "status": "online",
        "message": "OnePick Universal Downloader Engine with Proxy Active!"
    }

# ==============================================================================
# 3. Main Video Extraction Function (Proxy Integrated)
# ==============================================================================
def extract_video_info(video_url: str):
    # yt-dlp Configuration
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'mweb', 'android_vr']
            }
        }
    }

    # প্রক্সি সার্ভার পাস করা (YouTube Cloud IP Bot-Detection বাইপাস করার জন্য)
    if PROXY_URL:
        ydl_opts['proxy'] = PROXY_URL

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if not info:
                raise Exception("No video metadata found.")

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

                # Video streams filter
                if vcodec != 'none':
                    videos_list.append({
                        'resolution': res,
                        'height': f.get('height', 0),
                        'ext': ext,
                        'url': stream_url
                    })
                # Audio streams filter
                elif acodec != 'none':
                    audio_list.append({
                        'language': f.get('format_note', 'Audio Track'),
                        'bitrate': f"{int(f.get('tbr', 0))} kbps" if f.get('tbr') else "128 kbps",
                        'ext': ext,
                        'url': stream_url
                    })

            # Backup video format
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
                "uploader": info.get('uploader', 'Unknown'),
                "videos": videos_list[:12],
                "audio_tracks": audio_list[:5]
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Engine Error: {str(e)}")

# ==============================================================================
# 4. API Endpoints Setup (Swagger & Vercel Support)
# ==============================================================================
@app.get("/api/extract")
@app.get("/api/fetch")
def extract_get(url: str = Query(..., description="Target Media URL")):
    return extract_video_info(url.strip())

@app.post("/fetch")
@app.post("/api/fetch")
@app.post("/api/extract")
def extract_post(data: VideoRequest):
    return extract_video_info(data.url.strip())
