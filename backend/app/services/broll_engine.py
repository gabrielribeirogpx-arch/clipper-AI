from typing import Dict, List
import re

from app.services.keyword_mapper import KeywordMapper
from app.services.asset_matcher import AssetMatcher


class BRollEngine:
    """Detect keyword windows, build b-roll timeline and prepare overlay instructions."""

    def __init__(self) -> None:
        self.mapper = KeywordMapper()
        self.matcher = AssetMatcher()

    def _extract_keywords(self, text: str) -> List[str]:
        tokens = re.findall(r"[\w\-]+", text.lower())
        seen = []
        for token in tokens:
            if token not in seen:
                seen.append(token)
        return seen

    def build_timeline(self, transcription_segments: List[Dict]) -> List[Dict]:
        timeline = []

        for segment in transcription_segments:
            segment_text = segment.get("text", "")
            start = float(segment.get("start", 0))
            end = float(segment.get("end", start))

            keywords = self._extract_keywords(segment_text)
            for keyword in keywords:
                category = self.mapper.resolve_category(keyword)
                if not category:
                    continue

                asset = self.matcher.match(category)
                if not asset:
                    continue

                entry = {
                    "keyword": keyword,
                    "category": category,
                    "asset_path": asset,
                    "start": start,
                    "end": end,
                    "overlay": {
                        "position": "center",
                        "scale": 0.32,
                        "opacity": 0.95,
                    },
                    "transition": {
                        "fade_in": 0.2,
                        "fade_out": 0.2,
                    },
                }

                if not timeline or timeline[-1]["asset_path"] != asset or (start - timeline[-1]["end"]) > 0.6:
                    timeline.append(entry)
                else:
                    timeline[-1]["end"] = max(timeline[-1]["end"], end)

        return timeline
