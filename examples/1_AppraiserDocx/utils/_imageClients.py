import os
import requests

# GOOGLE:
def getSession(token):
    headers = {
        'Content-Type': 'application/json',
    }

    params = {
        'key': token,
    }

    json_data = {
        'mapType': 'satellite',
        'language': 'en-US',
        'region': 'US',
    }

    response = requests.post('https://tile.googleapis.com/v1/createSession', params=params, headers=headers, json=json_data)
    return response.json()['session']

def getGoogleTiles(x, y, zoom, temp_dir, token=""):
    """returns the path to the tile image and the size of the tile"""
    params = {
        'session': getSession(token),
        'key': token,
    }

    response = requests.get(f'https://tile.googleapis.com/v1/2dtiles/{zoom}/{x}/{y}', params=params)

    tile_path = os.path.join(temp_dir, f'google_{zoom}_{x}_{y}.png')
    with open(tile_path, 'wb') as f:
        f.write(response.content)
    return tile_path, 256

# MAPBOX (regrid style):
def getMapboxTiles(x, y, z, temp_dir, token=""):
    """returns the path to the tile image and the size of the tile"""
    url = f"https://api.mapbox.com/styles/v1/mapbox/streets-v11/tiles/{z}/{x}/{y}"
    querystring = { "access_token": "pk.eyJ1IjoibG92ZWxhbmQiLCJhIjoibHFTSURFNCJ9.titsQDMlSIud_r60hOlmeA" }

    headers = {
        "host": "api.mapbox.com",
        "connection": "keep-alive",
        "sec-ch-ua": "\"Not)A;Brand\";v=\"99\", \"Google Chrome\";v=\"127\", \"Chromium\";v=\"127\"",
        "sec-ch-ua-mobile": "?0",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "sec-ch-ua-platform": "\"Windows\"",
        "accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "sec-fetch-site": "cross-site",
        "sec-fetch-mode": "no-cors",
        "sec-fetch-dest": "image",
        "referer": "https://demos.regrid.com/",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9"
    }

    response = requests.get(url, headers=headers, params=querystring)
    tile_path = os.path.join(temp_dir, f"{z}_{x}_{y}.png")

    with open(tile_path, "wb") as f:
        f.write(response.content)

    return tile_path, 512