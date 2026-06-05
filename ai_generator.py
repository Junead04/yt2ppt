# -*- coding: utf-8 -*-
"""AI slide generation via Groq — produces rich, professional content."""
import json
import re
import requests

SYSTEM_PROMPT = """You are a world-class McKinsey-level presentation strategist and designer.
Your slides are used in boardrooms, conferences, and high-stakes pitches.

Given YouTube transcripts and instructions, create a POWERFUL, INSIGHT-RICH slide deck.

CRITICAL CONTENT RULES:
- Extract SPECIFIC facts, numbers, names, dates from transcripts — never be vague
- Every bullet must be a complete insight, not a topic label
  BAD: "AI is important"
  GOOD: "AI reduced operational costs by 40% in Fortune 500 companies by 2024"
- Stats slides must use REAL numbers from the transcripts
- Quotes must be ACTUAL statements from the video content
- Section slides must tease what's coming — create curiosity
- Closing slide must have clear, memorable takeaways

Return ONLY valid JSON — no markdown, no extra text. Schema:
{
  "title": "Specific, compelling title — not generic",
  "subtitle": "One punchy insight-driven subtitle",
  "theme": "tech|business|education|creative|science|health",
  "slides": [
    {
      "type": "title|section|content|two_col|stats|quote|image_focus|closing",
      "title": "Specific, action-oriented title",
      "subtitle": "Supporting context (title/section/closing only)",
      "body": [
        "Complete insight sentence with specific detail (max 15 words)",
        "Another specific insight with data or example",
        "Third insight — never filler, always substance"
      ],
      "left_title": "Left column label (two_col only)",
      "left_body": ["Specific point", "Another specific point"],
      "right_title": "Right column label (two_col only)",
      "right_body": ["Specific point", "Another specific point"],
      "stats": [
        {"value": "Exact number from transcript", "label": "What it measures"},
        {"value": "Another stat", "label": "Context"}
      ],
      "quote": "Exact or near-exact impactful statement from video content",
      "quote_author": "Speaker name or video title",
      "image_keyword": "3 specific words for photo search",
      "speaker_notes": "3 sentences: what to say, why it matters, transition to next slide"
    }
  ]
}

SLIDE TYPE STRATEGY:
- Slide 1: title — bold claim, not just a topic name
- Every 3-4 slides: section — create narrative momentum  
- content: 3-5 bullets, each a complete thought with specifics
- two_col: use for before/after, pros/cons, compare/contrast with REAL differences
- stats: only when you have 3-4 REAL numbers — make them striking
- quote: use the most memorable line from the transcripts
- image_focus: for emotional or conceptual moments — big idea, minimal text
- closing: 3-4 concrete takeaways the audience can act on

QUALITY CHECKLIST before outputting:
✓ Every bullet has a specific detail (number, name, example)
✓ No slide title is just a noun phrase — add a verb or insight
✓ Stats are real numbers, not placeholders
✓ Speaker notes give real talking points, not slide repetition
✓ image_keyword is specific (e.g. "rocket launch nasa" not just "space")"""

MAX_TRANSCRIPT_WORDS = 4000


def _trim_transcripts(transcripts_block: str) -> str:
    words = transcripts_block.split()
    if len(words) > MAX_TRANSCRIPT_WORDS:
        return " ".join(words[:MAX_TRANSCRIPT_WORDS]) + "\n[Trimmed for length]"
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
    user_msg = f"""VIDEO TRANSCRIPTS:
{trimmed}

USER INSTRUCTIONS:
{user_prompt}

Generate a {num_slides}-slide deck.

IMPORTANT:
- Pull SPECIFIC insights, numbers, and quotes directly from the transcripts
- Make every slide punchy and substantive — no filler content
- The audience should learn something new on every single slide
- Prioritize depth over breadth — fewer strong points beat many weak ones"""

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
            "temperature": 0.65,
        },
        timeout=90,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text[:400]}")
    return _parse_response(resp.json()["choices"][0]["message"]["content"])


def call_anthropic(transcripts_block: str, user_prompt: str, num_slides: int,
                   api_key: str, model: str) -> dict:
    trimmed = _trim_transcripts(transcripts_block)
    user_msg = f"""VIDEO TRANSCRIPTS:
{trimmed}

USER INSTRUCTIONS:
{user_prompt}

Generate a {num_slides}-slide deck with specific, insight-rich content from the transcripts."""

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
