import os

os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

from moviepy.editor import *


def create_tiktok_subtitles(video_path, segments, output_path):

    video = VideoFileClip(video_path)

    text_clips = []

    for segment in segments:

        words = segment.get("words", [])

        if not words:
            continue

        for word_data in words:

            if "start" not in word_data or "end" not in word_data:
                continue

            word = word_data["word"]

            word_start = word_data["start"]
            word_end = word_data["end"]

            txt_clip = (
                TextClip(
                    word.upper(),
                    fontsize=110,
                    font="Arial-Bold",
                    color="#FFD400",
                    stroke_color="black",
                    stroke_width=8,
                    kerning=-3,
                    method="caption",
                    size=(900, None),
                    align="center",
                )
                .set_start(word_start)
                .set_end(word_end)
                .set_position(("center", 1100))
            )

            shadow_clip = (
                TextClip(
                    word.upper(),
                    fontsize=110,
                    font="Arial-Bold",
                    color="black",
                    stroke_color="black",
                    stroke_width=10,
                    kerning=-3,
                    method="caption",
                    size=(900, None),
                    align="center",
                )
                .set_opacity(0.6)
                .set_start(word_start)
                .set_end(word_end)
                .set_position(("center", 1105))
            )

            text_clips.append(shadow_clip)
            text_clips.append(txt_clip)

    final = CompositeVideoClip([video, *text_clips])

    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=30
    )

    return output_path