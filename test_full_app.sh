export QT_QPA_PLATFORM="xcb"
xvfb-run -a -s "-screen 0 1920x1080x24" bash -c '
    cd /home/eirom/Projects/Pyrolist/src/pyrolist
    /home/eirom/Projects/Pyrolist/venv/bin/python main.py &
    PID=$!
    
    echo "Waiting for Pyrolist window..."
    for i in {1..30}; do
        WID=$(xdotool search --name "Pyrolist" | head -n 1)
        if [ ! -z "$WID" ]; then
            break
        fi
        sleep 1
    done
    
    if [ -z "$WID" ]; then
        echo "Could not find Pyrolist window after 30 seconds"
        kill $PID
        exit 1
    fi
    echo "Found window: $WID"
    
    # Wait for the app to fully load
    sleep 5
    
    # Click near the right edge for the notification button
    # Default size is 1300x820. Center of the window is usually placed at 0,0 by default in Xvfb, or somewhere
    # Let us get window geometry to be sure
    eval $(xdotool getwindowgeometry --shell $WID)
    echo "Window geometry: X=$X Y=$Y WIDTH=$WIDTH HEIGHT=$HEIGHT"
    
    TARGET_X=$(($X + $WIDTH - 40))
    TARGET_Y=$(($Y + 40))
    
    echo "Clicking at $TARGET_X, $TARGET_Y"
    xdotool mousemove $TARGET_X $TARGET_Y click 1
    sleep 2
    
    import -window root /home/eirom/Projects/Pyrolist/full_app_after.png
    
    kill $PID
'
