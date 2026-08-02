import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI(title="OnePick Media Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

# Render-এর Environment Variable থেকে কুকি তৈরি
COOKIES_PATH = "/tmp/yt_cookies.txt"
yt_cookies_env = os.getenv("YOUTUBE_COOKIES", "").strip()

if yt_cookies_env:
    with open(COOKIES_PATH, "w", encoding="utf-8") as f:
        f.write(yt_cookies_env)

@app.get("/")
def home():
    return {"status": "online", "message": "OnePick Universal Downloader Engine Active!"}

def extract_video_info(video_url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'nocheckcertificate': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en', 'bn', 'hi', 'es', 'all'],
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

    # কুকি ফাইল থাকলে তা যুক্ত করা হবে
    if os.path.exists(COOKIES_PATH) and os.path.getsize(COOKIES_PATH) > 0:
        ydl_opts['cookiefile'] = COOKIES_PATH

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if not info:
                raise Exception("No video metadata found.")

            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

            videos_list = []
            audio_list = []
            seen_formats = set()

            # ১. ভিডিও ও অডিও ফরম্যাট ফিল্টারিং
            for f in info.get('formats', []):
                stream_url = f.get('url')
                if not stream_url:
                    continue

                vcodec = f.get('vcodec', 'none')
                acodec = f.get('acodec', 'none')
                height = f.get('height', 0)
                ext = f.get('ext', 'mp4')
                fps = f.get('fps', '')
                
                # রেজোলিউশন ফরম্যাটিং (e.g. 1080p, 720p)
                res_label = f"{height}p" if height else f.get('format_note', 'SD')
                if fps and isinstance(fps, (int, float)) and fps > 30:
                    res_label += f"{int(fps)}"

                unique_key = f"{res_label}_{ext}_{vcodec!='none'}"

                if unique_key in seen_formats:
                    continue
                seen_formats.add(unique_key)

                # ভিডিও ফাইল (With or Without Audio)
                if vcodec != 'none':
                    videos_list.append({
                        'resolution': res_label,
                        'height': height or 0,
                        'ext': ext,
                        'has_audio': acodec != 'none',
                        'filesize_approx': f.get('filesize') or f.get('filesize_approx') or 0,
                        'url': stream_url
                    })
                # পিওর অডিও ফাইল
                elif acodec != 'none':
                    audio_list.append({
                        'language': f.get('language') or f.get('format_note', 'Audio Track'),
                        'bitrate': f"{int(f.get('tbr', 0))} kbps" if f.get('tbr') else "128 kbps",
                        'ext': ext,
                        'filesize_approx': f.get('filesize') or f.get('filesize_approx') or 0,
                        'url': stream_url
                    })

            # রেজোলিউশন অনুযায়ী শর্ট করা (উচ্চ রেজোলিউশন আগে থাকবে)
            videos_list = sorted(videos_list, key=lambda x: x['height'], reverse=True)

            # ২. সাবটাইটেল প্রসেসিং
            subtitles_list = []
            all_subs = info.get('subtitles') or info.get('automatic_captions') or {}
            for lang_code, sub_data in all_subs.items():
                for sub in sub_data:
                    if sub.get('ext') in ['vtt', 'srt', 'json3']:
                        subtitles_list.append({
                            'language': lang_code,
                            'ext': sub.get('ext'),
                            'url': sub.get('url')
                        })
                        break

            return {
                "success": True,
                "title": info.get('title', 'Media File'),
                "thumbnail": info.get('thumbnail', ''),
                "duration": info.get('duration', 0),
                "uploader": info.get('uploader', 'Unknown'),
                "platform": info.get('extractor_key', 'Generic'),
                "videos": videos_list[:15],
                "audio_tracks": audio_list[:8],
                "subtitles": subtitles_list[:10]
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Engine Error: {str(e)}")

@app.get("/api/extract")
@app.get("/api/fetch")
def extract_get(url: str = Query(..., description="Target Media URL")):
    return extract_video_info(url.strip())

@app.post("/fetch")
@app.post("/api/fetch")
@app.post("/api/extract")
def extract_post(data: VideoRequest):
    return extract_video_info(data.url.strip())
