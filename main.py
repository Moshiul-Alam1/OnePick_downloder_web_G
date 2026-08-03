import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
import yt_dlp

app = FastAPI(title="OnePick Universal Raw Metadata Engine")

# CORS Policy configuration so front-end can access the API smoothly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

# Cookies file path configuration from Render Environment Variable
COOKIES_PATH = "/tmp/yt_cookies.txt"
yt_cookies_env = os.getenv("YOUTUBE_COOKIES", "").strip()

if yt_cookies_env:
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        f.write(yt_cookies_env)

@app.get("/")
def home():
    return {
        "status": "online", 
        "message": "OnePick Complete Raw Data Extraction Engine Active!"
    }

def extract_all_video_info(video_url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'nocheckcertificate': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['all'],  # সমস্ত সাবটাইটেল ডাটা সংগ্রহ করবে
        'getcomments': False,      # ফেচিং ফাস্ট রাখতে কমেন্ট অফ রাখা হয়েছে (প্রয়োজনে True করতে পারো)
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'mweb', 'web']
            }
        }
    }

    # কুকি ফাইল থাকলে তা স্বয়ংক্রিয়ভাবে যুক্ত করে নিবে
    if os.path.exists(COOKIES_PATH) and os.path.getsize(COOKIES_PATH) > 0:
        ydl_opts['cookiefile'] = COOKIES_PATH

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # extract_info সরাসরি yt-dlp এর সম্পূর্ণ ডিকশনারি ডাটা ফেচ করে
            raw_info = ydl.extract_info(video_url, download=False)
            
            if not raw_info:
                raise Exception("No metadata could be extracted from this URL.")

            # sanitize_info নিশ্চিত করে যে সব অবজেক্ট জেসন পার্স করার উপযোগী
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

# GET Request Endpoints
@app.get("/api/extract")
@app.get("/api/fetch")
def extract_get(url: str = Query(..., description="Target Media URL")):
    return extract_all_video_info(url.strip())

# POST Request Endpoints
@app.post("/fetch")
@app.post("/api/fetch")
@app.post("/api/extract")
def extract_post(data: VideoRequest):
    return extract_all_video_info(data.url.strip())
