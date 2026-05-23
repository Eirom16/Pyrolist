import sys
import asyncio
import threading
import time
from PySide6.QtWidgets import QApplication
import qasync
from qt_material import build_stylesheet

app = QApplication(sys.argv)

async def main():
    loop = asyncio.get_event_loop()
    print('Starting thread...')
    
    def background_task(main_loop):
        start = time.time()
        qss = build_stylesheet(theme='dark_purple.xml', extra={'pyside6': True})
        elapsed = time.time() - start
        
        def apply_it():
            print(f'Done generating QSS in {elapsed:.2f}s! Size: {len(qss)}')
            app.quit()
            
        main_loop.call_soon_threadsafe(apply_it)
        
    threading.Thread(target=background_task, args=(loop,), daemon=True).start()

with qasync.QEventLoop(app) as loop:
    asyncio.set_event_loop(loop)
    loop.create_task(main())
    loop.run_forever()
