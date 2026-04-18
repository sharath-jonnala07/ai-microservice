from __future__ import annotations

import json
from pathlib import Path

from app.models.schemas import SourceRecord


def load_source_manifest(path: Path) -> list[SourceRecord]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [SourceRecord.model_validate(item) for item in data]


def enabled_sources(path: Path) -> list[SourceRecord]:
    return [source for source in load_source_manifest(path) if source.enabled]
