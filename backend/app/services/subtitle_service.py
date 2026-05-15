import pysrt
import os

SUBTITLES_DIR = "app/subtitles"

os.makedirs(SUBTITLES_DIR, exist_ok=True)

def seconds_to_srt_time(seconds):

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds - int(seconds)) * 1000)

    return pysrt.SubRipTime(
        hours=hours,
        minutes=minutes,
        seconds=secs,
        milliseconds=milliseconds
    )

def generate_srt(segments, filename):

    subs = pysrt.SubRipFile()

    for i, segment in enumerate(segments, start=1):

        sub = pysrt.SubRipItem(
            index=i,
            start=seconds_to_srt_time(segment["start"]),
            end=seconds_to_srt_time(segment["end"]),
            text=segment["text"]
        )

        subs.append(sub)

    output_path = f"{SUBTITLES_DIR}/{filename}.srt"

    subs.save(output_path, encoding="utf-8")

    return output_path