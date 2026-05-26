from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CACHE_DIR = Path("backend/app/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(analysis_id: str) -> Path:
    return CACHE_DIR / f"analysis_{analysis_id}.json"


def load_analysis_cache(analysis_id: str) -> dict[str, Any] | None:
    path = _cache_path(analysis_id)
    if not path.exists():
        print(f"[ANALYSIS CACHE MISS] analysis_id={analysis_id}")
        return None
    print(f"[ANALYSIS CACHE HIT] analysis_id={analysis_id}")
    data = json.loads(path.read_text())
    print(f"[CACHE RESTORED] path={path}")
    return data


def save_analysis_cache(analysis_id: str, payload: dict[str, Any]) -> None:
    path = _cache_path(analysis_id)
    path.write_text(json.dumps(payload, ensure_ascii=False))
    print(f"[CACHE SAVED] path={path}")
