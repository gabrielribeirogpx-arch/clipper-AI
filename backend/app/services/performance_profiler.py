from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


class PerformanceProfiler:
    def __init__(self, report_path: str | None = None):
        self._starts: dict[str, float] = {}
        self.metrics: dict[str, float] = {}
        self.metadata: dict[str, Any] = {}
        self._lock = threading.Lock()
        self.report_path = report_path

    def start_timer(self, label: str) -> None:
        with self._lock:
            self._starts[label] = time.perf_counter()

    def end_timer(self, label: str) -> float:
        with self._lock:
            start = self._starts.pop(label, None)
            elapsed = max(0.0, time.perf_counter() - start) if start else 0.0
            self.metrics[label] = self.metrics.get(label, 0.0) + elapsed
        print(f"[PERF] {label} = {elapsed:.1f}s")
        return elapsed

    def set_metric(self, label: str, value: float) -> None:
        self.metrics[label] = float(value)
        print(f"[PERF] {label} = {float(value):.1f}s")

    def set_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value

    def record_gpu_info(self) -> None:
        cuda_available = False
        torch_cuda = False
        try:
            import torch

            cuda_available = bool(torch.cuda.is_available())
            torch_cuda = cuda_available
            self.metadata["gpu_active"] = torch.cuda.get_device_name(0) if cuda_available else "none"
        except Exception:
            self.metadata["gpu_active"] = "unknown"
        self.metadata["cuda_available"] = cuda_available
        self.metadata["torch_cuda"] = torch_cuda
        self.metadata["encoder_used"] = os.getenv("VIDEO_ENCODER", "auto")
        self.metadata["ffmpeg_encoder"] = _detect_ffmpeg_encoder()
        print(f"[PERF GPU] encoder_used={self.metadata['encoder_used']}")
        print(f"[PERF GPU] gpu_active={self.metadata['gpu_active']}")
        print(f"[PERF GPU] cuda_available={self.metadata['cuda_available']}")
        print(f"[PERF GPU] torch_cuda={self.metadata['torch_cuda']}")
        print(f"[PERF GPU] ffmpeg_encoder={self.metadata['ffmpeg_encoder']}")

    def finalize(self) -> dict[str, Any]:
        total = sum(self.metrics.values())
        slowest_step = max(self.metrics, key=self.metrics.get) if self.metrics else "none"
        print(f"[PERF TOTAL PIPELINE] total={total:.1f}s")
        print(f"[PERF SLOWEST STEP] {slowest_step}={self.metrics.get(slowest_step, 0.0):.1f}s")
        payload = {**self.metrics, "total": round(total, 3), "slowest_step": slowest_step, "metadata": self.metadata}
        if self.report_path:
            path = Path(self.report_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        return payload


def _detect_ffmpeg_encoder() -> str:
    try:
        proc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True, check=False)
        out = proc.stdout or ""
        for enc in ("h264_nvenc", "hevc_nvenc", "h264_videotoolbox", "h264_qsv", "libx264"):
            if enc in out:
                return enc
    except Exception:
        return "unknown"
    return "unknown"
