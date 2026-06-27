from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class EncoderSelection:
    codec: str
    preset: str
    gpu: str


def _cmd_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _load_ffmpeg_encoders() -> str:
    try:
        proc = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            print("[FFMPEG ENCODERS LOADED]")
            return proc.stdout or ""
    except Exception as exc:
        print(f"[FFMPEG ENCODERS LOAD ERROR] {exc}")
    return ""


def _ffmpeg_has_encoder(encoders_text: str, name: str) -> bool:
    return name in encoders_text


def detect_best_encoder() -> EncoderSelection:
    # TODO(local-engine): keep GPU -> CPU fallback explicit for desktop/local engine builds;
    # expose the selected encoder in diagnostics before cloud APIs are reduced to licensing/sync.
    print("[GPU DETECTION START]")

    force_cpu = os.getenv("FORCE_CPU_ENCODER", "false").strip().lower() in {"1","true","yes","on"}
    if force_cpu:
        print("[CPU FALLBACK ACTIVE] forced=true")
        print("[ENCODER SELECTED] codec=libx264 preset=fast")
        return EncoderSelection(codec="libx264", preset="fast", gpu="cpu")

    try:
        if platform.system().lower() == "windows":
            print("[WINDOWS GPU DETECTION]")

        encoders = _load_ffmpeg_encoders()

        if _ffmpeg_has_encoder(encoders, "h264_nvenc") and _cmd_exists("nvidia-smi"):
            print("[NVENC AVAILABLE]")
            print("[ENCODER SELECTED] codec=h264_nvenc preset=p4")
            return EncoderSelection(codec="h264_nvenc", preset="p4", gpu="nvidia")

        if _ffmpeg_has_encoder(encoders, "h264_amf"):
            print("[ENCODER SELECTED] codec=h264_amf preset=balanced")
            return EncoderSelection(codec="h264_amf", preset="balanced", gpu="amd")

        if _ffmpeg_has_encoder(encoders, "h264_qsv"):
            print("[ENCODER SELECTED] codec=h264_qsv preset=fast")
            return EncoderSelection(codec="h264_qsv", preset="fast", gpu="intel")
    except Exception as exc:
        print(f"[GPU DETECTION ERROR] {exc}")

    print("[CPU FALLBACK ACTIVE] reason=no_hw_encoder")
    print("[ENCODER SELECTED] codec=libx264 preset=fast")
    return EncoderSelection(codec="libx264", preset="fast", gpu="cpu")
