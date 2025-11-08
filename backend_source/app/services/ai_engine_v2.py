# backend_source/app/services/ai_engine_v2.py
import os
import re
import random
import logging
from typing import List, Dict, Optional

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

#Simple helper: clean text and extract keywords
def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())

def _extract_keywords(text: str, top_n: int = 6) -> List[str]:
    # Very simple keyword heuristic: top frequent non-stopwords
    stopwords = set([
        "the","and","or","in","on","with","a","an","of","for","to","is","are","that","this","it","as","by","from"
    ])
    words = re.findall(r"[A-Za-z0-9']{2,}", text.lower())
    freq = {}
    for w in words:
        if w in stopwords: continue
        freq[w] = freq.get(w, 0) + 1
    items = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [w for w,_ in items][:top_n]

def _format_hashtags(keywords: List[str], max_tags: int = 10) -> List[str]:
    tags = []
    for kw in keywords:
        tag = "#" + re.sub(r"[^A-Za-z0-9]", "", kw)
        if len(tag) > 1:
            tags.append(tag)
        if len(tags) >= max_tags:
            break
    # Add a few trending generic tags as fallback
    fallback = ["#Viral", "#Trending", "#Creators"]
    for f in fallback:
        if f not in tags and len(tags) < max_tags:
            tags.append(f)
    return tags

# Local (non-OpenAI) caption generator
def _local_generate_caption(text: str, tone: str = "neutral", length: str = "short", platform: str = "generic") -> str:
    text = _clean_text(text)
    base = text if len(text) < 140 else text[:137] + "..."
    keywords = _extract_keywords(text, top_n=6)
    hashtags = " ".join(_format_hashtags(keywords, max_tags=4))
    cta = {
        "generic": "Learn more: link in bio",
        "instagram": "Check link in bio 👇",
        "youtube": "Watch full video on our channel ▶️",
        "linkedin": "Read the full piece on our site",
        "twitter": "RT if you found this helpful 🔁"
    }.get(platform.lower(), "Learn more: link in bio")
    if length == "short":
        caption = f"{base} {hashtags}"
    elif length == "long":
        caption = f"{base}\n\nKey points: {', '.join(keywords)}\n\n{cta} {hashtags}"
    else:
        caption = f"{base} {cta} {hashtags}"
    # tone adjust (very naive)
    if tone == "excited":
        caption = caption + " 🚀"
    return caption.strip()

# Try a provider (OpenAI) if key present
def _openai_generate(prompt: str, max_tokens: int = 200) -> Optional[str]:
    try:
        if not OPENAI_API_KEY:
            return None
        # Lazy import so we don't force dependency
        import openai
        openai.api_key = OPENAI_API_KEY
        resp = openai.Completion.create(
            engine="gpt-4o-mini", prompt=prompt, max_tokens=max_tokens, temperature=0.8
        )
        if resp and isinstance(resp.choices, list) and resp.choices:
            return resp.choices[0].text.strip()
    except Exception as e:
        logging.exception("OpenAI call failed: %s", e)
    return None

def generate_caption(text: str, tone: str = "neutral", length: str = "short", platform: str = "generic") -> str:
    text = _clean_text(text)
    # If provider available, craft a prompt
    if OPENAI_API_KEY:
        prompt = f"Write a {length} {tone} social media caption tailored for {platform}. Keep brand voice professional. Content:\n\n{text}\n\nInclude 3 hashtags and a short CTA."
        out = _openai_generate(prompt, max_tokens=150)
        if out:
            return out
    # fallback:
    return _local_generate_caption(text, tone=tone, length=length, platform=platform)

def generate_hashtags(text: str, max_tags: int = 8) -> List[str]:
    text = _clean_text(text)
    keywords = _extract_keywords(text, top_n=max_tags*2)
    tags = _format_hashtags(keywords, max_tags=max_tags)
    # If provider present, try to get trending tag suggestions
    if OPENAI_API_KEY:
        prompt = f"Suggest up to {max_tags} relevant hashtags (no explanation) for this text:\n\n{text}\n\nReturn only hashtags separated by commas."
        out = _openai_generate(prompt, max_tokens=80)
        if out:
            # parse possible comma separated result
            cand = re.findall(r"#\w+", out)
            if cand:
                return cand[:max_tags]
    return tags

def summarize_video(transcript: str, max_sentences: int = 3) -> str:
    t = _clean_text(transcript)
    if OPENAI_API_KEY:
        prompt = f"Summarize the following video transcript in {max_sentences} concise sentences:\n\n{t}"
        out = _openai_generate(prompt, max_tokens=180)
        if out:
            return out
    # naive heuristic: first N sentences
    sents = re.split(r'(?<=[.!?])\s+', t)
    s = " ".join(sents[:max_sentences]).strip()
    return s if s else t[:200] + "..."
