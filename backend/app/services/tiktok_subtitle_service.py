from __future__ import annotations

import os
from typing import Dict, List

from moviepy.editor import CompositeVideoClip, VideoFileClip

from app.services.reframing_service import ReframingService
from app.services.subtitle_renderer import SubtitleRenderer

os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"


def _collect_words(segments: List[Dict]) -> List[Dict]:
    words: List[Dict] = []
    for segment in segments:
        segment_words = segment.get("words", [])
        if segment_words:
            words.extend(segment_words)
    return words


def create_tiktok_subtitles(video_path, segments, output_path):
    """Render premium subtitles and export video.

    API intentionally unchanged.
    """
    video = VideoFileClip(video_path)
    reframer = ReframingService()
    reframed_video = reframer.apply(video)

    renderer = SubtitleRenderer()
    word_layers = renderer.build_word_layers(
        words=_collect_words(segments),
        video_w=int(reframed_video.w),
        video_h=int(reframed_video.h),
    )

    final_video = CompositeVideoClip([reframed_video, *word_layers])
    final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

    final_video.close()
    reframed_video.close()
    if reframed_video is not video:
        video.close()

    return output_path
