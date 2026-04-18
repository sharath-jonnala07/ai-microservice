from __future__ import annotations

import logging
from uuid import uuid4

from app.core.config import Settings
from app.ingestion.chunking import create_splitter
from app.ingestion.loaders import fetch_source_text
from app.models.schemas import ChunkRecord
from app.services.source_manifest import enabled_sources
from app.services.vector_index import VectorIndexRepository


LOGGER = logging.getLogger(__name__)


def run_ingestion(settings: Settings) -> int:
    sources = [source for source in enabled_sources(settings.source_manifest_path) if source.allow_for_answers]
    splitter = create_splitter()
    chunks: list[ChunkRecord] = []

    for source in sources:
        try:
            text = fetch_source_text(source, settings.user_agent, settings.request_timeout_seconds)
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Skipping source %s because fetch failed: %s", source.source_id, exc)
            continue
        if not text.strip():
            LOGGER.warning("Skipping source %s because extracted text was empty", source.source_id)
            continue

        for index, chunk_text in enumerate(splitter.split_text(text)):
            normalized = " ".join(chunk_text.split())
            if len(normalized) < 80:
                continue
            chunks.append(
                ChunkRecord(
                    chunk_id=str(uuid4()),
                    source_id=source.source_id,
                    source_title=source.title,
                    source_url=source.url,
                    authority=source.authority,
                    document_type=source.document_type,
                    published_at=source.published_at,
                    chunk_index=index,
                    text=normalized,
                    tags=source.tags,
                    scheme_names=source.scheme_names,
                )
            )

    if not chunks:
        raise RuntimeError("No source chunks were generated. Update or verify the manifest and retry ingestion.")

    repository = VectorIndexRepository(settings)
    repository.build(chunks)
    return len(chunks)
