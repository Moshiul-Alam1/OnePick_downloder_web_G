import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

PROXY_URL = os.getenv("PROXY_URL", "").strip()

@app.get("/")
def home():
    return {"status": "online", "message": "OnePick Universal Downloader Engine Active!"}

def fetch_with_ytdlp(video_url: str, use_proxy: bool = True):
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

    # প্রক্সি শুধুমাত্র তখনই ব্যবহার করা হবে যদি প্রক্সি এনাবল রাখা হয়
    if use_proxy and PROXY_URL:
        ydl_opts['proxy'] = PROXY_URL

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
            "uploader": info.get('uploader', 'Unknown'),
            "videos": videos_list[:12],
            "audio_tracks": audio_list[:5]
        }

def extract_video_info(video_url: str):
    # ফেসবুক বা অন্যান্য সাইটের জন্য প্রক্সি দরকার নাও হতে পারে।
    # তাই প্রথমে প্রক্সি সহ ট্রাই করবে, প্রক্সিতে 407/ProxyError আসলে প্রক্সি ছাড়াই ফেচ করবে।
    try:
        return fetch_with_ytdlp(video_url, use_proxy=True)
    except Exception as e:
        error_msg = str(e)
        if "Proxy" in error_msg or "407" in error_msg:
            # প্রক্সি ফেইল করলে সরাসরি রেন্ডারের আইপি দিয়ে ট্রাই করবে (ফেসবুকের জন্য কাজ করে যাবে)
            try:
                return fetch_with_ytdlp(video_url, use_proxy=False)
            except Exception as direct_e:
                raise HTTPException(status_code=500, detail=f"Direct Engine Error: {str(direct_e)}")
        else:
            raise HTTPException(status_code=500, detail=f"Engine Error: {error_msg}")

@app.get("/api/extract")
@app.get("/api/fetch")
def extract_get(url: str = Query(..., description="Target Media URL")):
    return extract_video_info(url.strip())

@app.post("/fetch")
@app.post("/api/fetch")
@app.post("/api/extract")
def extract_post(data: VideoRequest):
    return extract_video_info(data.url.strip())
