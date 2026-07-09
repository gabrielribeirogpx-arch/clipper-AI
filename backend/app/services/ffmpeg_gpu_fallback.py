from __future__ import annotations

import shlex
import subprocess
from collections.abc import Sequence
from typing import Any

NVENC_CODEC = "h264_nvenc"
CPU_CODEC = "libx264"
CPU_PRESET = "veryfast"
FALLBACK_LOG = "[GPU FALLBACK]\nNVENC unavailable for this source.\nSwitching to libx264."

_NVENC_ONLY_OPTIONS_WITH_VALUES = {"-extra_hw_frames", "-surfaces", "-gpu", "-rc", "-cq", "-spatial-aq", "-temporal-aq"}
_NVENC_ONLY_FLAGS = {"-zerolatency", "-nonref_p"}
_HARDWARE_DECODE_OPTIONS_WITH_VALUES = {"-hwaccel", "-hwaccel_output_format", "-hwaccel_device"}


def _replace_option_value(command: list[str], option: str, value: str) -> None:
    try:
        index = command.index(option)
    except ValueError:
        return
    if index + 1 < len(command):
        command[index + 1] = value


def _remove_options(command: list[str], options_with_values: set[str], flags: set[str]) -> list[str]:
    sanitized: list[str] = []
    skip_next = False
    for part in command:
        if skip_next:
            skip_next = False
            continue
        if part in options_with_values:
            skip_next = True
            continue
        if part in flags:
            continue
        sanitized.append(part)
    return sanitized


def _ensure_option_before_output(command: list[str], option: str, value: str) -> None:
    if option in command:
        _replace_option_value(command, option, value)
        return
    output_index = max(len(command) - 1, 0)
    command[output_index:output_index] = [option, value]


def build_libx264_fallback_command(command: Sequence[str]) -> list[str]:
    fallback = list(command)
    _replace_option_value(fallback, "-c:v", CPU_CODEC)
    _replace_option_value(fallback, "-vcodec", CPU_CODEC)
    _replace_option_value(fallback, "-codec:v", CPU_CODEC)
    _replace_option_value(fallback, "-preset", CPU_PRESET)

    if "-tune" in fallback:
        tune_index = fallback.index("-tune")
        if tune_index + 1 < len(fallback) and fallback[tune_index + 1] == "ll":
            del fallback[tune_index:tune_index + 2]

    fallback = _remove_options(
        fallback,
        _NVENC_ONLY_OPTIONS_WITH_VALUES | _HARDWARE_DECODE_OPTIONS_WITH_VALUES,
        _NVENC_ONLY_FLAGS,
    )
    _ensure_option_before_output(fallback, "-pix_fmt", "yuv420p")
    return fallback


def command_uses_nvenc(command: Sequence[str]) -> bool:
    return NVENC_CODEC in command


def run_ffmpeg_with_gpu_fallback(
    command: Sequence[str],
    *,
    timeout: float | None = None,
    check: bool = False,
    capture_output: bool = True,
    text: bool = True,
    log_prefix: str = "[FFMPEG]",
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Run FFmpeg and retry with libx264 when h264_nvenc fails at runtime."""
    command_list = list(command)
    print(f"{log_prefix} command={' '.join(shlex.quote(part) for part in command_list)}")
    proc = subprocess.run(
        command_list,
        capture_output=capture_output,
        text=text,
        check=False,
        timeout=timeout,
        **kwargs,
    )
    if proc.returncode == 0 or not command_uses_nvenc(command_list):
        if check and proc.returncode != 0:
            proc.check_returncode()
        return proc

    print(FALLBACK_LOG)
    fallback_command = build_libx264_fallback_command(command_list)
    print(f"{log_prefix} fallback_command={' '.join(shlex.quote(part) for part in fallback_command)}")
    fallback_proc = subprocess.run(
        fallback_command,
        capture_output=capture_output,
        text=text,
        check=False,
        timeout=timeout,
        **kwargs,
    )
    if check and fallback_proc.returncode != 0:
        fallback_proc.check_returncode()
    return fallback_proc
