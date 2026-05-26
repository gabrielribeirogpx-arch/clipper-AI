from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

CACHE_DIR = Path("backend/app/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_path(analysis_id: str) -> Path:
    return CACHE_DIR / f"analysis_{analysis_id}.json"


def load_analysis_cache(analysis_id: str) -> dict[str, Any] | None:
    start = time.perf_counter()
    path = _cache_path(analysis_id)
    if not path.exists():
        print(f"[ANALYSIS CACHE MISS] analysis_id={analysis_id}")
        print("[PERF CACHE] miss")
        return None
    print(f"[ANALYSIS CACHE HIT] analysis_id={analysis_id}")
    data = json.loads(path.read_text())
    print(f"[CACHE RESTORED] path={path}")
    print("[PERF CACHE] hit")
    print(f"[PERF] cache_restore_time = {time.perf_counter() - start:.1f}s")
    return data


def save_analysis_cache(analysis_id: str, payload: dict[str, Any]) -> None:
    start = time.perf_counter()
    path = _cache_path(analysis_id)
    path.write_text(json.dumps(payload, ensure_ascii=False))
    print(f"[CACHE SAVED] path={path}")
    print(f"[PERF] cache_save_time = {time.perf_counter() - start:.1f}s")
