# -*- coding: utf-8 -*-
"""AI slide generation via Groq or Anthropic — uses requests library."""
import json
import re
import requests

SYSTEM_PROMPT = """You are a world-class presentation designer and content strategist.
Given YouTube video transcripts and instructions, create a stunning, insightful slide deck.

Return ONLY valid JSON — no markdown fences, no extra text. Schema:
{
  "title": "Compelling deck title",
  "subtitle": "One punchy subtitle line",
  "theme": "tech|business|education|creative|science|health",
  "slides": [
    {
      "type": "title|section|content|two_col|stats|quote|image_focus|closing",
      "title": "Slide title",
      "subtitle": "Optional subtitle (title/section/closing only)",
      "body": ["bullet point (max 12 words)", "..."],
      "left_title": "Left column header (two_col only)",
      "left_body": ["...", "..."],
      "right_title": "Right column header (two_col only)",
      "right_body": ["...", "..."],
      "stats": [{"value": "87%", "label": "Short label"}, ...],
      "quote": "Impactful quote text (quote type only)",
      "quote_author": "Author name",
      "image_keyword": "2-3 word search term for this slide photo",
      "speaker_notes": "2-3 sentences of presenter talking points"
    }
  ]
}

Rules:
- Slide 1: ALWAYS type=title, Last slide: ALWAYS type=closing
- Use section for major transitions, two_col for comparisons
- Use stats for key numbers (3-4 stats max), quote for powerful statements
- Use image_focus for visual impact slides
- content slides: max 5 bullets, each under 12 words
- ALWAYS fill image_keyword and speaker_notes for every slide
- Extract real insights from transcripts — be specific not generic"""

# Max words to send to AI — keeps within free tier limits
MAX_TRANSCRIPT_WORDS = 3500


def _trim_transcripts(transcripts_block: str) -> str:
    """Trim total transcript to stay within token limits."""
    words = transcripts_block.split()
    if len(words) > MAX_TRANSCRIPT_WORDS:
        trimmed = " ".join(words[:MAX_TRANSCRIPT_WORDS])
        return trimmed + "\n\n[Transcripts trimmed to fit AI token limit]"
    return transcripts_block


def _parse_response(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'^```\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)


def call_groq(transcripts_block: str, user_prompt: str, num_slides: int,
              api_key: str, model: str) -> dict:

    trimmed = _trim_transcripts(transcripts_block)
    user_msg = (
        f"VIDEO TRANSCRIPTS:\n{trimmed}\n\n"
        f"USER INSTRUCTIONS:\n{user_prompt}\n\n"
        f"Generate a {num_slides}-slide deck. Extract real insights. Be specific."
    )

    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        timeout=90,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text[:400]}")
    return _parse_response(resp.json()["choices"][0]["message"]["content"])


def call_anthropic(transcripts_block: str, user_prompt: str, num_slides: int,
                   api_key: str, model: str) -> dict:

    trimmed = _trim_transcripts(transcripts_block)
    user_msg = (
        f"VIDEO TRANSCRIPTS:\n{trimmed}\n\n"
        f"USER INSTRUCTIONS:\n{user_prompt}\n\n"
        f"Generate a {num_slides}-slide deck. Extract real insights. Be specific."
    )

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": model,
            "max_tokens": 4096,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_msg}],
        },
        timeout=90,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Anthropic API error {resp.status_code}: {resp.text[:400]}")
    return _parse_response(resp.json()["content"][0]["text"])


def generate_slides(transcripts_block: str, user_prompt: str, num_slides: int,
                    api_key: str, provider: str, model: str) -> dict:
    if provider == "Groq (Free)":
        return call_groq(transcripts_block, user_prompt, num_slides, api_key, model)
    return call_anthropic(transcripts_block, user_prompt, num_slides, api_key, model)
