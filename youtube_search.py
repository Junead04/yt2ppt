# -*- coding: utf-8 -*-
"""YouTube search + transcript fetching.
- YouTube Data API v3 for search
- Supadata API for transcripts (works from cloud, no IP blocking)
- Falls back to youtube-transcript-api for local use
"""
import re
import requests


def extract_video_id(url: str):
    patterns = [
        r'(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})',
        r'(?:embed/)([A-Za-z0-9_-]{11})',
        r'(?:shorts/)([A-Za-z0-9_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def search_youtube(query: str, yt_api_key: str, max_results: int = 5):
    """Search YouTube and return list of video dicts."""
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "order": "relevance",
        "videoCaption": "closedCaption",
        "key": yt_api_key,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    results = []
    for item in data.get("items", []):
        vid_id = item["id"]["videoId"]
        snippet = item["snippet"]
        results.append({
            "vid_id": vid_id,
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "description": snippet.get("description", "")[:200],
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
        })
    return results


def get_transcript_supadata(video_id: str, api_key: str, max_words: int = 1200):
    """Fetch transcript via Supadata API — works from cloud servers."""
    try:
        url = "https://api.supadata.ai/v1/youtube/transcript"
        headers = {"x-api-key": api_key}
        params = {"videoId": video_id, "text": "true"}
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        if resp.status_code == 404:
            return "", "No transcript available for this video"
        if resp.status_code == 402:
            return "", "Supadata free tier limit reached"
        if resp.status_code != 200:
            return "", f"Supadata error {resp.status_code}"
        data = resp.json()
        # Supadata returns either 'content' (plain text) or 'chunks'
        text = ""
        if isinstance(data, dict):
            if "content" in data:
                text = data["content"]
            elif "chunks" in data:
                text = " ".join(c.get("text", "") for c in data["chunks"])
            elif "transcript" in data:
                text = data["transcript"]
        elif isinstance(data, str):
            text = data
        if not text:
            return "", "Empty transcript returned"
        words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words]) + "..."
        return text, ""
    except Exception as e:
        return "", str(e)


def get_transcript_local(video_id: str, max_words: int = 1200):
    """Fallback: use youtube-transcript-api for local development."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        USE_FETCH = hasattr(YouTubeTranscriptApi, 'fetch') and not hasattr(YouTubeTranscriptApi, 'get_transcript')
        if USE_FETCH:
            ytt = YouTubeTranscriptApi()
            try:
                obj = ytt.fetch(video_id, languages=["en", "en-US", "en-GB"])
            except Exception:
                obj = ytt.fetch(video_id)
            text = " ".join(
                s.text if hasattr(s, 'text') else s.get('text', '')
                for s in obj
            )
        else:
            segs = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US", "en-GB"])
            text = " ".join(s["text"] for s in segs)
        words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words]) + "..."
        return text, ""
    except Exception as e:
        return "", str(e)


def get_transcript(video_id: str, supadata_key: str = "", max_words: int = 1200):
    """Smart transcript fetcher — Supadata if key provided, else local."""
    if supadata_key:
        return get_transcript_supadata(video_id, supadata_key, max_words)
    return get_transcript_local(video_id, max_words)


def fetch_transcripts_from_urls(urls: list, supadata_key: str = ""):
    results = []
    errors = []
    for url in urls:
        vid_id = extract_video_id(url.strip())
        if not vid_id:
            errors.append(f"Could not parse video ID: {url}")
            continue
        text, err = get_transcript(vid_id, supadata_key)
        if err:
            errors.append(f"{vid_id}: {err}")
        else:
            results.append({
                "vid_id": vid_id,
                "url": url.strip(),
                "title": vid_id,
                "thumbnail": "",
                "channel": "",
                "text": text,
                "source": "manual",
            })
    return results, errors


def fetch_transcripts_from_search(query: str, yt_api_key: str,
                                   supadata_key: str = "", max_videos: int = 4):
    videos = search_youtube(query, yt_api_key, max_results=max_videos + 3)
    results = []
    errors = []
    for v in videos:
        if len(results) >= max_videos:
            break
        text, err = get_transcript(v["vid_id"], supadata_key)
        if err:
            errors.append(f'"{v["title"][:50]}": {err}')
            continue
        results.append({**v, "text": text, "source": "search"})
    return results, errors, videos
