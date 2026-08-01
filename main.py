from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI()

# Frontend থেকে Access দেওয়ার জন্য CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "OnePick Web Downloader API is Active!"}

@app.get("/api/extract")
def extract_video_info(url: str):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            videos = []
            audio_tracks = []
            has_4k = False

            if 'formats' in info:
                for f in info['formats']:
                    height = f.get('height') or 0
                    
                    # Check for 4K / High Quality
                    if height > 1080:
                        has_4k = True
                        continue # 4K এভোয়েড করে 1080p পর্যন্ত ফিল্টার করা
                    
                    # 1. Video Formats (Up to 1080p)
                    if f.get('vcodec') != 'none':
                        res_name = f.get('format_note') or f"{height}p" if height else "Video"
                        videos.append({
                            'resolution': res_name,
                            'height': height,
                            'ext': f.get('ext', 'mp4'),
                            'url': f.get('url')
                        })
                    
                    # 2. Specific Separate Audio Tracks (Languages & Bitrates)
                    elif f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                        lang = f.get('language') or 'Default/Original'
                        bitrate = f"{int(f.get('abr', 0))} kbps" if f.get('abr') else 'Audio'
                        audio_tracks.append({
                            'language': f"{lang.upper()} Track",
                            'bitrate': bitrate,
                            'ext': f.get('ext', 'm4a'),
                            'url': f.get('url')
                        })

            # Sort & Deduplicate Videos up to 1080p
            unique_videos = {}
            for v in videos:
                if v['height'] <= 1080 and v['height'] not in unique_videos:
                    unique_videos[v['height']] = v

            sorted_videos = sorted(unique_videos.values(), key=lambda x: x['height'], reverse=True)

            return {
                "title": info.get('title', 'Media Download'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration'),
                "videos": sorted_videos, # 1080p, 720p, 480p etc.
                "audio_tracks": audio_tracks,
                "has_4k": has_4k, # 4K আছে কিনা ফ্লাগ
                "subtitles": list(info.get('subtitles', {}).keys())
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))