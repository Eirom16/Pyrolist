export QT_QPA_PLATFORM="xcb"
xvfb-run -a -s "-screen 0 1920x1080x24" bash -c '
    cd /home/eirom/Projects/Pyrolist/src/pyrolist
    /home/eirom/Projects/Pyrolist/venv/bin/python main.py &
    PID=$!
    sleep 10
    
    # Try to find the window
    WID=$(xdotool search --name "Pyrolist" | head -n 1)
    if [ -z "$WID" ]; then
        echo "Could not find Pyrolist window"
        kill $PID
        exit 1
    fi
    echo "Found window: $WID"
    
    # Take screenshot before
    import -window root /home/eirom/Projects/Pyrolist/before.png
    
    # The window is maximized in 1920x1080? PySide6 might not maximize it.
    # The default size is 1300x820.
    # So the notification button is near the right edge of 1300.
    xdotool mousemove 1250 50 click 1
    sleep 1
    
    # Take screenshot after
    import -window root /home/eirom/Projects/Pyrolist/after.png
    
    kill $PID
'
