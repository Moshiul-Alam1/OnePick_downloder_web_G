from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yt_dlp

app = FastAPI()

# Enable CORS for Vercel Frontend
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
def read_root():
    return {"message": "OnePick Web Downloader Engine Active!"}

@app.post("/api/fetch")
def fetch_media_info(data: VideoRequest):
    url = data.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required.")

    # Universal yt-dlp Configuration for all 1000+ supported sites
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Handling Playlists / Multi-video links
            if 'entries' in info:
                info = info['entries'][0]

            formats = []
            raw_formats = info.get('formats', [])
            
            # Filter and organize formats cleanly
            for f in raw_formats:
                url_link = f.get('url')
                if not url_link:
                    continue
                
                res = f.get('resolution') or f"{f.get('width', '')}x{f.get('height', '')}"
                if res == 'x':
                    res = f.get('format_note', 'Audio/Video')
                
                ext = f.get('ext', 'mp4')
                filesize = f.get('filesize') or f.get('filesize_approx')
                
                # Exclude 4K or ultra-heavy untranscodable streams if desired, keep standard up to 1080p
                height = f.get('height') or 0
                if height > 1080:
                    continue

                formats.append({
                    'format_id': f.get('format_id'),
                    'ext': ext,
                    'resolution': res,
                    'height': height,
                    'filesize': filesize,
                    'url': url_link,
                    'has_video': f.get('vcodec') != 'none',
                    'has_audio': f.get('acodec') != 'none'
                })

            return {
                "success": True,
                "title": info.get('title', 'Media Content'),
                "thumbnail": info.get('thumbnail', ''),
                "duration": info.get('duration', 0),
                "uploader": info.get('uploader') or info.get('extractor_key', 'Unknown Provider'),
                "site": info.get('extractor_key', 'Web'),
                "formats": formats
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch content: {str(e)}")