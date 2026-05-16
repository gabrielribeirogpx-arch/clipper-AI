from __future__ import annotations

import re
from collections import Counter
from typing import Dict, Iterable, List

STOP_WORDS = {
    "the", "and", "for", "that", "this", "with", "from", "you", "your", "are", "was", "were",
    "have", "has", "had", "they", "them", "their", "what", "when", "where", "will", "just",
    "about", "into", "then", "than", "there", "here", "out", "not", "all", "can", "but", "why",
    "how", "who", "our", "its", "his", "her", "him", "she", "himself", "herself", "also", "too",
    "been", "being", "did", "does", "doing", "is", "it", "a", "an", "of", "to", "in", "on", "at"
}

TITLE_TEMPLATES = [
    "THIS CHANGES EVERYTHING",
    "NO ONE SAW THIS COMING",
    "THE INTERNET IS DIVIDED OVER THIS",
    "HE DID NOT EXPECT THIS",
    "THIS ESCALATED FAST",
]


def _extract_keywords(text: str, limit: int = 5) -> List[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9']+", text.lower())
    filtered = [token for token in tokens if token not in STOP_WORDS and len(token) > 3]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(limit)]


def _best_quote(sentences: Iterable[str]) -> str:
    cleaned = [s.strip() for s in sentences if s.strip()]
    if not cleaned:
        return ""
    ranked = sorted(cleaned, key=lambda s: abs(len(s) - 70))
    return ranked[0]


def _title_from_text(text: str, viral_score: float) -> str:
    upper_text = text.upper()
    if "?" in text:
        return "EVERYONE IS ASKING THIS"
    if any(word in upper_text for word in ["NEVER", "NO WAY", "IMPOSSIBLE"]):
        return "YOU WON'T BELIEVE THIS TURN"
    if viral_score >= 88:
        return "THIS MOMENT CHANGED EVERYTHING"
    if viral_score >= 78:
        return "THE INTERNET IS DIVIDED OVER THIS"
    return TITLE_TEMPLATES[int(viral_score) % len(TITLE_TEMPLATES)]


def generate_social_metadata(clip_text: str, viral_score: float) -> Dict[str, str | List[str]]:
    sentences = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+", clip_text) if chunk.strip()]
    primary_line = _best_quote(sentences)
    keywords = _extract_keywords(clip_text, limit=6)

    title = _title_from_text(clip_text, viral_score)

    summary_seed = primary_line or (clip_text[:140].strip() + "...")
    description = (
        f"{summary_seed[:140]} "
        "Watch to the end for the reaction everyone is talking about."
    ).strip()

    caption_focus = keywords[0] if keywords else "this"
    caption = f"this {caption_focus} moment got out of control 😳 wait for the ending"

    hashtags = ["#viral", "#shorts"]
    hashtags.extend(f"#{word.replace("'", "")}" for word in keywords[:4])

    deduped_tags = list(dict.fromkeys(hashtags))[:6]

    return {
        "title": title,
        "description": description,
        "caption": caption,
        "hashtags": deduped_tags,
    }
