import yt_dlp
import time
from pyrolist.config.paths import AppDirs
import json

def test_headers():
    cookie_file = AppDirs.config / "headers_auth.json"
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    if cookie_file.exists():
        with open(cookie_file) as f:
            data = json.load(f)
            cookie_str = data.get('cookie', '')
            if cookie_str:
                opts['http_headers'] = {
                    'Cookie': cookie_str,
                    'User-Agent': data.get('user-agent', '')
                }
    
    start = time.time()
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info("https://www.youtube.com/watch?v=Dprsjlxj3QU", download=False)
    print(f"Extraction took {time.time() - start:.2f} seconds")

test_headers()
