from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List

from urllib import error as urlerror
from urllib import request as urlrequest

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
CACHE_LOCK = threading.Lock()


def metadata_enabled() -> bool:
    return os.getenv("AI_METADATA_ENABLED", "true").lower() not in {"0", "false", "no", "off"}


def timeout_seconds() -> float:
    try:
        return max(0.5, float(os.getenv("AI_METADATA_TIMEOUT_SECONDS", "8")))
    except ValueError:
        return 8.0


def max_clips() -> int:
    try:
        return max(0, int(os.getenv("AI_METADATA_MAX_CLIPS", "5")))
    except ValueError:
        return 5


def _first_sentence(text: str) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return "Trecho selecionado automaticamente."
    match = re.search(r"(.{12,}?[.!?])(?:\s|$)", cleaned)
    return (match.group(1) if match else cleaned[:120]).strip()


def no_ai_metadata(clip: Dict[str, Any], index: int = 0) -> Dict[str, Any]:
    text = clip.get("text", "")
    hook = _first_sentence(text)
    description = (" ".join(str(text).split())[:260] or hook).strip()
    if len(" ".join(str(text).split())) > 260:
        description += "..."
    score = clip.get("viral_score", clip.get("score", 0))
    return {
        "score": score,
        "emotion": "Não analisado",
        "category": "Auto",
        "titles": [f"Clip {index + 1:02d}"],
        "description": description,
        "viral_reason": "Gerado por detecção heurística; IA de metadata indisponível.",
        "hook": hook,
        "provider": "none",
        "metadata_status": "no_ai",
    }


def _sanitize(raw: Dict[str, Any], clip: Dict[str, Any], index: int, provider: str) -> Dict[str, Any]:
    fallback = no_ai_metadata(clip, index)
    titles = raw.get("titles") if isinstance(raw.get("titles"), list) else []
    clean_titles = [str(t).strip() for t in titles if str(t).strip()]
    if not clean_titles:
        clean_titles = fallback["titles"]
    try:
        score = int(float(raw.get("score", fallback["score"])))
    except (TypeError, ValueError):
        score = fallback["score"]
    if isinstance(score, (int, float)):
        score = max(0, min(100, int(score)))
    return {
        "score": score,
        "emotion": str(raw.get("emotion") or fallback["emotion"]).strip(),
        "category": str(raw.get("category") or fallback["category"]).strip(),
        "titles": clean_titles[:3],
        "description": str(raw.get("description") or fallback["description"]).strip(),
        "viral_reason": str(raw.get("viral_reason") or fallback["viral_reason"]).strip(),
        "hook": str(raw.get("hook") or fallback["hook"]).strip(),
        "provider": provider,
        "metadata_status": "ai",
    }


def _prompt(transcript: str) -> str:
    return f"""Analise este clip para TikTok, Shorts e Reels. Responda somente JSON estrito, sem markdown, com as chaves: score, emotion, category, titles, description, viral_reason, hook. titles deve ter 3 opções curtas. score deve ser 0-100.\n\nTranscrição:\n{transcript.strip()}"""


def _parse_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def _cache_path(output_dir: str | None) -> Path:
    root = Path(output_dir or "app/clips")
    root.mkdir(parents=True, exist_ok=True)
    return root / "ai_metadata_cache.json"


def cache_key(clip: Dict[str, Any]) -> str:
    seed = f"{clip.get('text','')}|{clip.get('start')}|{clip.get('end')}"
    return hashlib.sha256(seed.encode("utf-8", "ignore")).hexdigest()


def _read_cache(output_dir: str | None) -> Dict[str, Any]:
    path = _cache_path(output_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_cache(output_dir: str | None, cache: Dict[str, Any]) -> None:
    _cache_path(output_dir).write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def select_provider() -> str:
    configured = os.getenv("AI_METADATA_PROVIDER", "auto").lower().strip()
    if not metadata_enabled() or configured == "none":
        provider = "none"
    elif configured == "gemini":
        provider = "gemini" if os.getenv("GEMINI_API_KEY") else "none"
    elif configured == "ollama":
        provider = "ollama"
    else:
        provider = "gemini" if os.getenv("GEMINI_API_KEY") else "none"
    print(f"[AI_METADATA_PROVIDER_SELECTED] provider={provider} configured={configured}")
    return provider


def _gemini(clip: Dict[str, Any], index: int) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY missing")
    print(f"[AI_METADATA_REQUEST_START] provider=gemini index={index}")
    body = json.dumps({"contents": [{"parts": [{"text": _prompt(clip.get('text', ''))}]}], "generationConfig": {"responseMimeType": "application/json"}}).encode("utf-8")
    req = urlrequest.Request(f"{GEMINI_URL}?key={api_key}", data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlrequest.urlopen(req, timeout=timeout_seconds()) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    return _sanitize(_parse_json(text), clip, index, "gemini")


def _ollama(clip: Dict[str, Any], index: int) -> Dict[str, Any]:
    print(f"[AI_METADATA_REQUEST_START] provider=ollama index={index}")
    body = json.dumps({"model": OLLAMA_MODEL, "prompt": _prompt(clip.get("text", "")), "stream": False, "format": "json"}).encode("utf-8")
    req = urlrequest.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlrequest.urlopen(req, timeout=timeout_seconds()) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return _sanitize(_parse_json(payload.get("response", "{}")), clip, index, "ollama")


def generate_metadata(clip: Dict[str, Any], index: int = 0, output_dir: str | None = None, provider: str | None = None) -> Dict[str, Any]:
    selected = provider or select_provider()
    key = cache_key(clip)
    with CACHE_LOCK:
        cache = _read_cache(output_dir)
        if key in cache:
            print(f"[AI_METADATA_CACHE_HIT] index={index}")
            return cache[key]
    if selected == "none":
        print(f"[AI_METADATA_FALLBACK_NO_AI] index={index} reason=provider_none")
        return no_ai_metadata(clip, index)
    try:
        meta = _gemini(clip, index) if selected == "gemini" else _ollama(clip, index)
        print(f"[AI_METADATA_SUCCESS] provider={selected} index={index}")
    except TimeoutError:
        print(f"[AI_METADATA_TIMEOUT] provider={selected} index={index}")
        meta = no_ai_metadata(clip, index)
    except urlerror.URLError as error:
        if isinstance(getattr(error, "reason", None), TimeoutError):
            print(f"[AI_METADATA_TIMEOUT] provider={selected} index={index}")
        else:
            print(f"[AI_METADATA_FALLBACK_NO_AI] provider={selected} index={index} error={type(error).__name__}: {error}")
        meta = no_ai_metadata(clip, index)
    except Exception as error:
        print(f"[AI_METADATA_FALLBACK_NO_AI] provider={selected} index={index} error={type(error).__name__}: {error}")
        meta = no_ai_metadata(clip, index)
    if meta.get("metadata_status") == "ai":
        with CACHE_LOCK:
            cache = _read_cache(output_dir)
            cache[key] = meta
            _write_cache(output_dir, cache)
    return meta


def apply_metadata_to_clip(clip: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    updated = dict(clip)
    titles = meta.get("titles") or [updated.get("title_suggestion") or "Clip"]
    updated.update({
        "viral_score": meta.get("score", updated.get("viral_score", 0)),
        "title_suggestion": titles[0],
        "caption_suggestion": meta.get("hook", updated.get("caption_suggestion", "")),
        "description_suggestion": meta.get("description", updated.get("description_suggestion", "")),
        "emotion": meta.get("emotion", updated.get("emotion", "Não analisado")),
        "category": meta.get("category", updated.get("category", "Auto")),
        "viral_reason": meta.get("viral_reason", updated.get("viral_reason", "")),
        "title_options": titles,
        "metadata_status": meta.get("metadata_status", "no_ai"),
        "metadata_provider": meta.get("provider", "none"),
    })
    return updated
