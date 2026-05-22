import sys
import os
import asyncio
from PySide6.QtWidgets import QApplication
from pyrolist.main import async_setup
from pyrolist.ui.main_window import MainWindow

async def simulate_play(window: MainWindow):
    print("Waiting for app to load...")
    await asyncio.sleep(3)
    print("Playing Dprsjlxj3QU")
    window._play_song_sync(
        video_id="Dprsjlxj3QU", 
        title="La Ruta J", 
        artist="Artist", 
        thumbnail_url="", 
        duration_ms=200000, 
        album=""
    )
    print("Waiting for stream extraction...")
    for _ in range(20):
        await asyncio.sleep(1)
        if window.queue.current and window.queue.current.stream_url:
            print("Successfully extracted:", window.queue.current.stream_url)
            break
    else:
        print("Timeout waiting for stream!")
    
    QApplication.quit()

async def main():
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    app = QApplication(sys.argv)
    yt, player, settings_mgr, db, mpris, discord_rpc, scrobbler, crossfade_manager, lyrics_client, download_manager = await async_setup()
    
    window = MainWindow(yt, player, settings_mgr, db, mpris, discord_rpc, scrobbler, crossfade_manager, lyrics_client, download_manager)
    window.show()
    
    asyncio.create_task(simulate_play(window))
    
    # Run the event loop inside asyncio using qasync
    import qasync
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    asyncio.run(main())
