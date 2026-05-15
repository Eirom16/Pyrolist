from ytmusicapi import YTMusic
import json

headers = {"cookie": "VISITOR_INFO1_LIVE=xyz;"}
with open("test_headers.json", "w") as f:
    json.dump(headers, f)

try:
    yt = YTMusic("test_headers.json")
    print("YTMusic initialized successfully with headers file")
except Exception as e:
    print(f"Error: {e}")
