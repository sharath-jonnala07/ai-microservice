"""Fact lookup service — deterministic answers from pre-extracted fact table."""
from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass

from app.services.question_classifier import Classification

_FACT_TABLE_PATH = Path(__file__).resolve().parents[2] / "data" / "facts" / "fact_table.json"


@dataclass(slots=True)
class FactResult:
    answer: str
    source_id: str
    source_title: str
    source_url: str


class FactLookupService:
    """Loads the fact table once and provides O(1) lookups."""

    def __init__(self) -> None:
        self._table: dict = {}
        self._load()

    def _load(self) -> None:
        with open(_FACT_TABLE_PATH, encoding="utf-8") as f:
            self._table = json.load(f)

    def lookup(self, classification: Classification) -> FactResult | None:
        """Return a FactResult if the fact table has a deterministic answer."""
        if classification.fact_type is None:
            return None

        # Scheme-specific lookup
        if classification.scheme is not None:
            scheme_data = self._table.get(classification.scheme)
            if scheme_data:
                fact = scheme_data.get(classification.fact_type)
                if fact:
                    return FactResult(
                        answer=fact["answer"],
                        source_id=fact["source_id"],
                        source_title=fact["source_title"],
                        source_url=fact["source_url"],
                    )

        # General / cross-scheme facts
        general_data = self._table.get("_general", {})
        fact = general_data.get(classification.fact_type)
        if fact:
            return FactResult(
                answer=fact["answer"],
                source_id=fact["source_id"],
                source_title=fact["source_title"],
                source_url=fact["source_url"],
            )

        return None
