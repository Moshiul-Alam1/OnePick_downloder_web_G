import os
import base64
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
import yt_dlp

app = FastAPI(title="OnePick Universal Data Extraction Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

# Cookies configuration using Base64 Decoding
COOKIES_PATH = "/tmp/yt_cookies.txt"
b64_cookies = os.getenv("YOUTUBE_COOKIES_BASE64", "").strip()

# Base64 না থাকলে সাধারণ Plain Text Cookies fallback চেক করবে
plain_cookies = os.getenv("YOUTUBE_COOKIES", "").strip()

if b64_cookies:
    try:
        decoded_bytes = base64.b64decode(b64_cookies)
        with open(COOKIES_PATH, "wb") as f:
            f.write(decoded_bytes)
    except Exception as e:
        print(f"Base64 Cookie Decoding Error: {e}")
elif plain_cookies:
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        f.write(plain_cookies)

@app.get("/")
def home():
    return {
        "status": "online", 
        "message": "OnePick Universal Downloader Engine Active!"
    }

def extract_all_video_info(video_url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'nocheckcertificate': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['all'],
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        },
        # Client Player Strategy: android/web_creator ব্যবহার করলে ইউটিউব ব্লক এড়ানো যায়
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'android', 'ios'],
                'player_skip': ['configs', 'webpage']
            }
        }
    }

    # চেক করা হচ্ছে ফাইলটি তৈরি হয়েছে কি না এবং এর সাইজ ১০ বাইটের বেশি কি না
    if os.path.exists(COOKIES_PATH) and os.path.getsize(COOKIES_PATH) > 10:
        ydl_opts['cookiefile'] = COOKIES_PATH

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            raw_info = ydl.extract_info(video_url, download=False)
            
            if not raw_info:
                raise Exception("No metadata found.")

            sanitized_data = ydl.sanitize_info(raw_info)

            return {
                "success": True,
                "data": jsonable_encoder(sanitized_data)
            }

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail={"success": False, "error": f"Engine Error: {str(e)}"}
        )

@app.get("/api/extract")
@app.get("/api/fetch")
def extract_get(url: str = Query(..., description="Target Media URL")):
    return extract_all_video_info(url.strip())

@app.post("/fetch")
@app.post("/api/fetch")
@app.post("/api/extract")
def extract_post(data: VideoRequest):
    return extract_all_video_info(data.url.strip())
