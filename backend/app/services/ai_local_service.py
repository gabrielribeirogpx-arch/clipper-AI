from __future__ import annotations

import json
from typing import Any, Dict, List

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"
REQUEST_TIMEOUT_SECONDS = 25

FALLBACK_METADATA: Dict[str, Any] = {
    "score": 50,
    "emotion": "neutro",
    "category": "curiosidade",
    "titles": [
        "Esse momento vai te surpreender",
        "Você não esperava esse desfecho",
        "O detalhe que muda tudo aqui",
    ],
    "description": "Trecho com potencial de retenção e curiosidade para redes sociais.",
    "viral_reason": "Combina curiosidade com progressão narrativa que incentiva assistir até o fim.",
    "hook": "Preste atenção nos primeiros segundos: o contexto muda rápido.",
}


def _sanitize_metadata(raw: Dict[str, Any]) -> Dict[str, Any]:
    titles = raw.get("titles") if isinstance(raw.get("titles"), list) else []
    clean_titles: List[str] = [str(title).strip() for title in titles if str(title).strip()]
    if len(clean_titles) < 3:
        fallback_titles = FALLBACK_METADATA["titles"]
        clean_titles.extend(fallback_titles[len(clean_titles):3])

    score_value = raw.get("score", FALLBACK_METADATA["score"])
    try:
        score = int(float(score_value))
    except (TypeError, ValueError):
        score = FALLBACK_METADATA["score"]
    score = max(0, min(100, score))

    return {
        "score": score,
        "emotion": str(raw.get("emotion") or FALLBACK_METADATA["emotion"]).strip(),
        "category": str(raw.get("category") or FALLBACK_METADATA["category"]).strip(),
        "titles": clean_titles[:3],
        "description": str(raw.get("description") or FALLBACK_METADATA["description"]).strip(),
        "viral_reason": str(raw.get("viral_reason") or FALLBACK_METADATA["viral_reason"]).strip(),
        "hook": str(raw.get("hook") or FALLBACK_METADATA["hook"]).strip(),
    }


def generate_clip_metadata(transcript: str) -> Dict[str, Any]:
    if not transcript or not transcript.strip():
        return FALLBACK_METADATA.copy()

    prompt = f"""Você é um algoritmo especialista em retenção viral para TikTok, Shorts e Reels.

Analise o trecho enviado.

Considere:
- gancho inicial
- emoção
- polêmica
- humor
- curiosidade
- quebra de padrão
- retenção
- impacto psicológico
- potencial de comentários

Retorne JSON válido:

{{
  \"score\": 0-100,
  \"emotion\": \"...\",
  \"category\": \"...\",
  \"titles\": [
    \"...\",
    \"...\",
    \"...\"
  ],
  \"description\": \"...\",
  \"viral_reason\": \"...\",
  \"hook\": \"...\"
}}

Trecho:
{transcript.strip()}
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    try:
        print(f"[OLLAMA REQUEST] url={OLLAMA_URL} model={OLLAMA_MODEL} chars={len(transcript)}")
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        envelope = response.json()
        print(f"[OLLAMA RESPONSE] status={response.status_code} body={envelope}")

        raw_json = envelope.get("response")
        if not raw_json:
            raise ValueError("Resposta do Ollama veio vazia")

        parsed = json.loads(raw_json)
        return _sanitize_metadata(parsed)

    except (requests.RequestException, ValueError, json.JSONDecodeError) as error:
        print(f"[OLLAMA ERROR] {type(error).__name__}: {error}")
        return FALLBACK_METADATA.copy()
