from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

# ==============================================================================
# 1. CORS Middleware (Vercel Frontend Cross-Origin Request Allow করার জন্য)
# ==============================================================================
# বিবরণ: Vercel থেকে পাঠানো যেকোনো HTTP রিকোয়েস্ট যাতে Render ব্লক না করে,
#       তার জন্য সব ধরনের Origin, Method এবং Header এখানে অ্যালাউ করা হয়েছে।
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

# ==============================================================================
# 2. Health Check Root Route
# ==============================================================================
# বিবরণ: সার্ভার অনলাইন আছে কিনা ব্রাউজারে ডাইরেক্ট চেক করার জন্য।
# ==============================================================================
@app.get("/")
def home():
    return {"status": "online", "message": "OnePick Engine is Running Perfect!"}


# ==============================================================================
# 3. Main Extraction Logic Function
# ==============================================================================
# বিবরণ: ভিডিও লিংক প্রসেস করার আসল ইঞ্জিন। ইউটিউব, ফেসবুক, টিকটক ইত্যাদির লিংক
#       থেকে ডাউনলোডেবল স্ট্রিমিং ইউআরএল এবং মেটাডেটা বের করে।
# ==============================================================================
def process_video_extraction(video_url: str):
    # YouTube Cloud Server Bot-Detection Bypass Configuration
    # -------------------------------------------------------
    # কারণ: Render/Cloud Server IP কে ইউটিউব বোট মনে করে ব্লক করে ("Sign in to confirm you're not a bot")।
    # সমাধান: yt-dlp কে নির্দেশ দেওয়া হচ্ছে যেন সে সাধারণ ওয়েব ব্রাউজারের বদলে Android VR, iOS,
    #        এবং Mobile Web (mweb) প্লেয়ার ক্লায়েন্ট হিসেবে রিকোয়েস্ট পাঠায়।
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'skip_download': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
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
            
            if not info:
                raise Exception("No video metadata found.")

            # প্লেলিস্ট বা মাল্টি-এন্ট্রি ভিডিও হলে ১ম ভিডিওটি ফিল্টার করার জন্য
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

            videos_list = []
            audio_list = []

            # ভিডিও এবং অডিও ফরম্যাট আলাদা করে কাস্টম রেসপন্স তৈরি করা
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

                # ভিডিও স্ট্রিম থাকলে
                if vcodec != 'none':
                    videos_list.append({
                        'resolution': res,
                        'height': f.get('height', 0),
                        'ext': ext,
                        'url': stream_url
                    })
                # শুধু অডিও স্ট্রিম থাকলে
                elif acodec != 'none':
                    audio_list.append({
                        'language': f.get('format_note', 'Audio Track'),
                        'bitrate': f"{int(f.get('tbr', 0))} kbps" if f.get('tbr') else "128 kbps",
                        'ext': ext,
                        'url': stream_url
                    })

            # কোনো রেজুলেশন আলাদা না পাইলে মেইন ডাইরেক্ট ইউআরএল ব্যাকআপ হিসেবে রাখা
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
                "site": info.get('extractor_key', 'Web'),
                "videos": videos_list[:12], # সেরা ১২টি কোয়ালিটি লিংক
                "audio_tracks": audio_list[:5],
                "has_4k": any(v.get('height', 0) >= 2160 for v in videos_list)
            }

    except Exception as e:
        error_msg = str(e)
        if "Sign in to confirm" in error_msg:
            raise Exception("YouTube restrictions active on cloud IP. Please try another link or use OnePick Desktop App.")
        raise Exception(error_msg)


# ==============================================================================
# 4. Endpoints Setup (404 Error পুরোপুরি দূর করার জন্য)
# ==============================================================================
# বিবরণ: GET এবং POST—দুই ধরণের রিকোয়েস্টই সাপোর্ট করবে। Swagger UI এবং Vercel 
#       ফ্রন্টএন্ডের সবকয়টি পরিচিত রুটে (`/api/extract`, `/api/fetch`, `/fetch`) 
#       এটা ম্যাচ করানো আছে।

# A. GET Method for Swagger and Vercel Frontend
@app.get("/api/extract")
@app.get("/api/fetch")
def extract_get(url: str = Query(..., description="Media Target URL")):
    video_url = url.strip()
    if not video_url:
        raise HTTPException(status_code=400, detail="Please provide a valid URL")
    try:
        return process_video_extraction(video_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# B. POST Method Fallback
@app.post("/fetch")
@app.post("/api/fetch")
@app.post("/api/extract")
def extract_post(data: VideoRequest):
    video_url = data.url.strip()
    if not video_url:
        raise HTTPException(status_code=400, detail="Please provide a valid URL")
    try:
        return process_video_extraction(video_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
