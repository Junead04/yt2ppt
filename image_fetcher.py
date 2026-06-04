"""Fetch slide background images — Pexels primary, Pixabay fallback."""
import requests
import os
import urllib.request


def fetch_pexels(keyword: str, api_key: str) -> str | None:
    try:
        url = "https://api.pexels.com/v1/search"
        params = {"query": keyword, "per_page": 3, "orientation": "landscape"}
        headers = {"Authorization": api_key}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        photos = data.get("photos", [])
        if not photos:
            return None
        img_url = photos[0]["src"]["large"]
        tmp_path = f"/tmp/slide_px_{abs(hash(keyword)) % 99999}.jpg"
        urllib.request.urlretrieve(img_url, tmp_path)
        return tmp_path if os.path.exists(tmp_path) else None
    except Exception:
        return None


def fetch_pixabay(keyword: str, api_key: str) -> str | None:
    try:
        url = "https://pixabay.com/api/"
        params = {
            "key": api_key, "q": keyword,
            "image_type": "photo", "orientation": "horizontal",
            "per_page": 3, "safesearch": "true",
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return None
        hits = resp.json().get("hits", [])
        if not hits:
            return None
        img_url = hits[0]["largeImageURL"]
        tmp_path = f"/tmp/slide_pb_{abs(hash(keyword)) % 99999}.jpg"
        urllib.request.urlretrieve(img_url, tmp_path)
        return tmp_path if os.path.exists(tmp_path) else None
    except Exception:
        return None


def get_slide_image(keyword: str, pexels_key: str = "", pixabay_key: str = "") -> str | None:
    """Pexels first, Pixabay fallback."""
    if pexels_key:
        path = fetch_pexels(keyword, pexels_key)
        if path:
            return path
    if pixabay_key:
        path = fetch_pixabay(keyword, pixabay_key)
        if path:
            return path
    return None
