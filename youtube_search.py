# -*- coding: utf-8 -*-
"""YouTube Data API v3 — search + transcript fetching.
Compatible with youtube-transcript-api v0.x and v1.x
"""
import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi

# ── Handle both old (0.x) and new (1.x) versions ─────────────────────────────
try:
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
except ImportError:
    try:
        from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound
    except ImportError:
        TranscriptsDisabled = Exception
        NoTranscriptFound = Exception

# Detect API version: v1.x has fetch(), v0.x has get_transcript()
USE_FETCH = hasattr(YouTubeTranscriptApi, 'fetch') and not hasattr(YouTubeTranscriptApi, 'get_transcript')


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


def get_transcript(video_id: str, max_words: int = 1200):
    """Fetch English transcript. Returns (text, error_string).
    Works with both youtube-transcript-api v0.x and v1.x
    """
    try:
        if USE_FETCH:
            # ── v1.x API ──────────────────────────────────────────────────────
            ytt_api = YouTubeTranscriptApi()
            try:
                transcript_obj = ytt_api.fetch(video_id, languages=["en", "en-US", "en-GB"])
            except Exception:
                # fallback: try without language filter
                transcript_obj = ytt_api.fetch(video_id)
            # v1.x returns a FetchedTranscript object — iterate it
            text = " ".join(
                snippet.text if hasattr(snippet, 'text') else snippet.get('text', '')
                for snippet in transcript_obj
            )
        else:
            # ── v0.x API ──────────────────────────────────────────────────────
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id, languages=["en", "en-US", "en-GB"]
            )
            text = " ".join(seg["text"] for seg in transcript)

        words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words]) + "..."
        return text, ""

    except TranscriptsDisabled:
        return "", "Transcripts disabled for this video"
    except NoTranscriptFound:
        return "", "No English transcript found"
    except Exception as e:
        return "", str(e)


def fetch_transcripts_from_urls(urls: list):
    """Given a list of YouTube URLs, return fetched transcripts."""
    results = []
    errors = []
    for url in urls:
        vid_id = extract_video_id(url.strip())
        if not vid_id:
            errors.append(f"Could not parse video ID: {url}")
            continue
        text, err = get_transcript(vid_id)
        if err:
            errors.append(f"{vid_id}: {err}")
        else:
            results.append({
                "vid_id": vid_id,
                "url": url.strip(),
                "title": vid_id,
                "text": text,
                "source": "manual",
            })
    return results, errors


def fetch_transcripts_from_search(query: str, yt_api_key: str, max_videos: int = 5):
    """Search YouTube and fetch transcripts from top results."""
    videos = search_youtube(query, yt_api_key, max_results=max_videos + 3)
    results = []
    errors = []
    for v in videos:
        if len(results) >= max_videos:
            break
        text, err = get_transcript(v["vid_id"])
        if err:
            errors.append(f'"{v["title"]}": {err}')
            continue
        results.append({
            **v,
            "text": text,
            "source": "search",
        })
    return results, errors, videos
