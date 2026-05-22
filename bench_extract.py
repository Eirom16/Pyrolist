import time
import yt_dlp
from pyrolist.config.paths import AppDirs

def bench(format_filter):
    cookie_file = str(AppDirs.config / "cookies.txt")
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'cookiefile': cookie_file
    }
    if format_filter:
        opts['format'] = format_filter
        
    start = time.time()
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.extract_info("https://www.youtube.com/watch?v=Dprsjlxj3QU", download=False)
    print(f"Format {format_filter}: {time.time() - start:.2f} seconds")

if __name__ == '__main__':
    bench('bestaudio/best')
    bench(None)
