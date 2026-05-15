def detect_hooks(transcription):

    segments = transcription["segments"]

    hooks = []

    last_end = 0

    for segment in segments:

        duration = segment["end"] - segment["start"]

        if duration < 4:
            continue

        if segment["start"] < last_end:
            continue

        start = max(segment["start"] - 2, 0)

        end = start + 30

        hook = {
            "start": start,
            "end": end,
            "text": segment["text"],
            "words": segment.get("words", [])
        }

        hooks.append(hook)

        last_end = end

    return hooks[:3]