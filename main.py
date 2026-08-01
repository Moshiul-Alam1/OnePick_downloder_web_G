from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

# CORS bypass all origins
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
    return {"status": "online", "message": "OnePick Engine is Running Perfect!"}

# Dual endpoint setup to completely eliminate 404 Not Found error
@app.post("/fetch")
@app.post("/api/fetch")
def extract_video(data: VideoRequest):
    video_url = data.url.strip()
    if not video_url:
        raise HTTPException(status_code=400, detail="Please provide a valid URL")

    # Universal yt-dlp Configuration
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
                'player_client': ['android', 'ios', 'mweb']
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

            formats_list = []
            for f in info.get('formats', []):
                stream_url = f.get('url')
                if not stream_url:
                    continue

                res = f.get('resolution') or f"{f.get('width', '')}x{f.get('height', '')}"
                if res == 'x' or not res:
                    res = f.get('format_note', 'Standard')

                formats_list.append({
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext', 'mp4'),
                    'resolution': res,
                    'url': stream_url,
                    'has_video': f.get('vcodec') != 'none',
                    'has_audio': f.get('acodec') != 'none'
                })

            return {
                "success": True,
                "title": info.get('title', 'Media File'),
                "thumbnail": info.get('thumbnail', ''),
                "duration": info.get('duration', 0),
                "uploader": info.get('uploader', 'Unknown'),
                "site": info.get('extractor_key', 'Web'),
                "formats": formats_list
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download engine error: {str(e)}")
