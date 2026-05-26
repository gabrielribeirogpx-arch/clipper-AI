from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass


@dataclass
class EncoderSelection:
    codec: str
    preset: str
    gpu: str


def _cmd_exists(cmd: str) -> bool:
    proc = subprocess.run(["bash", "-lc", f"command -v {cmd}"], capture_output=True, text=True, check=False)
    return proc.returncode == 0


def _ffmpeg_has_encoder(name: str) -> bool:
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True, check=False)
    return proc.returncode == 0 and name in (proc.stdout or "")


def detect_best_encoder() -> EncoderSelection:
    force_cpu = os.getenv("FORCE_CPU_ENCODER", "false").strip().lower() in {"1","true","yes","on"}
    if force_cpu:
        print("[CPU FALLBACK] forced=true")
        print("[ENCODER SELECTED] codec=libx264 preset=fast")
        return EncoderSelection(codec="libx264", preset="fast", gpu="cpu")

    if _ffmpeg_has_encoder("h264_nvenc") and _cmd_exists("nvidia-smi"):
        print("[GPU DETECTED] vendor=nvidia")
        print("[NVENC ACTIVE]")
        print("[ENCODER SELECTED] codec=h264_nvenc preset=p4")
        return EncoderSelection(codec="h264_nvenc", preset="p4", gpu="nvidia")
    if _ffmpeg_has_encoder("h264_amf"):
        print("[GPU DETECTED] vendor=amd")
        print("[ENCODER SELECTED] codec=h264_amf preset=balanced")
        return EncoderSelection(codec="h264_amf", preset="balanced", gpu="amd")
    if _ffmpeg_has_encoder("h264_qsv"):
        print("[GPU DETECTED] vendor=intel")
        print("[ENCODER SELECTED] codec=h264_qsv preset=fast")
        return EncoderSelection(codec="h264_qsv", preset="fast", gpu="intel")

    print("[CPU FALLBACK] reason=no_hw_encoder")
    print("[ENCODER SELECTED] codec=libx264 preset=fast")
    return EncoderSelection(codec="libx264", preset="fast", gpu="cpu")
