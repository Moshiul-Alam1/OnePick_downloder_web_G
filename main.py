from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

# CORS Fix: Vercel ফ্রন্টএন্ড থেকে সব রিকোয়েস্ট অ্যালাউ করা
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    url: str

# Root route to check backend health
@app.get("/")
def read_root():
    return {"status": "ok", "message": "OnePick Engine Active"}

# Target Endpoint for Fetching
@app.post("/api/fetch")

def fetch_media(data: VideoRequest):
    url = data.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")

    # Advanced Bypass Configuration for Cloud Servers (Render)
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'skip_download': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        },
        # YouTube Specific Bypass
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'mweb'],
                'skip': ['hls', 'dash']
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if not info:
                raise HTTPException(status_code=404, detail="No video data found.")

            # If playlist or multi-entry, pick the first video
            if 'entries' in info and info['entries']:
                info = info['entries'][0]

            formats = []
            raw_formats = info.get('formats', [])

            for f in raw_formats:
                download_url = f.get('url')
                if not download_url:
                    continue

                res = f.get('resolution') or f"{f.get('width', '')}x{f.get('height', '')}"
                if res == 'x' or not res:
                    res = f.get('format_note', 'Audio/Video')

                ext = f.get('ext', 'mp4')
                filesize = f.get('filesize') or f.get('filesize_approx') or 0

                formats.append({
                    'format_id': f.get('format_id'),
                    'ext': ext,
                    'resolution': res,
                    'filesize': filesize,
                    'url': download_url,
                    'has_video': f.get('vcodec') != 'none',
                    'has_audio': f.get('acodec') != 'none'
                })

            return {
                "success": True,
                "title": info.get('title', 'Media Link'),
                "thumbnail": info.get('thumbnail', ''),
                "duration": info.get('duration', 0),
                "uploader": info.get('uploader') or info.get('extractor_key', 'Platform'),
                "site": info.get('extractor_key', 'Web'),
                "formats": formats
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
