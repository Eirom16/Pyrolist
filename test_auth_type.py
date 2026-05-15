import ytmusicapi
import json

headers = {
    "cookie": "SAPISID=123; __Secure-3PAPISID=456;", 
    "x-goog-authuser": "0", 
    "authorization": "SAPISIDHASH 1"
}
with open("browser.json", "w") as f:
    json.dump(headers, f)

try:
    yt = ytmusicapi.YTMusic("browser.json")
    print("Success loading browser.json!")
    print(yt._auth_type)
    print(yt.headers["authorization"])
except Exception as e:
    print(e)
