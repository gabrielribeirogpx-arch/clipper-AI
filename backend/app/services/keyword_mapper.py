from dataclasses import dataclass
from typing import Dict, List, Optional
import re


@dataclass(frozen=True)
class KeywordRule:
    keyword: str
    aliases: List[str]
    category: str


class KeywordMapper:
    """Map normalized words from transcription into b-roll categories."""

    def __init__(self) -> None:
        self.rules: List[KeywordRule] = [
            KeywordRule("dinheiro", ["dinheiro", "grana", "cash", "money"], "money"),
            KeywordRule("carro", ["carro", "carros", "veículo", "auto", "car"], "car"),
            KeywordRule("tiktok", ["tiktok", "tik tok"], "tiktok"),
            KeywordRule("negócio", ["negocio", "negócio", "empresa", "business"], "business"),
            KeywordRule("marketing", ["marketing", "anúncio", "anuncio", "ads"], "marketing"),
        ]

        self._alias_index: Dict[str, str] = {}
        for rule in self.rules:
            for alias in rule.aliases:
                self._alias_index[self._normalize(alias)] = rule.category

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.lower()).strip()

    def resolve_category(self, raw_text: str) -> Optional[str]:
        normalized = self._normalize(raw_text)
        return self._alias_index.get(normalized)
