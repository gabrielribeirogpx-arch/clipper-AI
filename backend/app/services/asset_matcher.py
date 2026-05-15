from pathlib import Path
from typing import Dict, Optional


ASSET_BASE_DIR = Path("app/assets/broll")


class AssetMatcher:
    """Find best asset for each b-roll category."""

    def __init__(self) -> None:
        self.category_assets: Dict[str, str] = {
            "money": "money.mp4",
            "car": "car.mp4",
            "tiktok": "tiktok.mp4",
            "business": "business.mp4",
            "marketing": "marketing.mp4",
        }

    def match(self, category: str) -> Optional[str]:
        filename = self.category_assets.get(category)
        if not filename:
            return None

        candidate = ASSET_BASE_DIR / filename
        if candidate.exists():
            return str(candidate)

        # fallback to image asset for same category if video doesn't exist
        image_candidate = ASSET_BASE_DIR / filename.replace(".mp4", ".png")
        if image_candidate.exists():
            return str(image_candidate)

        return None
