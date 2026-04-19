from __future__ import annotations

from dataclasses import dataclass
import re

from app.core.config import Settings
from app.models.schemas import ChunkRecord, Citation
from app.services.question_classifier import expand_query_with_synonyms
from app.services.vector_index import VectorIndexRepository


@dataclass(slots=True)
class RetrievedSource:
    citation: Citation
    context: str


PROCESS_TYPES = {"support_process", "statement_guidance", "forms_page", "portal", "reference_links"}
SCHEME_FACT_TYPES = {"kim", "sid", "factsheet", "ter_notice", "ter_reference"}
PROCESS_PATTERN = re.compile(r"download|statement|capital gains|tax|account statement|cas")
EXPENSE_PATTERN = re.compile(r"expense ratio|ter|total expense")
SCHEME_FACT_PATTERN = re.compile(r"exit load|minimum sip|\bsip\b|lock-in|lock in|benchmark|riskometer|risk-o-meter|fund manager|investment objective|fund type|plans and options|minimum investment|min lumpsum|aum|assets under management|fund size")
FUND_MANAGER_PATTERN = re.compile(r"fund manager|managed by|who manages|portfolio manager")


class SourceRetriever:
    def __init__(self, repository: VectorIndexRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    def is_ready(self) -> bool:
        return self._repository.is_ready()

    def retrieve(self, question: str) -> RetrievedSource | None:
        expanded_question = expand_query_with_synonyms(question)
        hits = self._repository.search(expanded_question, k=max(self._settings.retrieval_k * 3, 24))
        if not hits:
            return None

        grouped_scores: dict[str, float] = {}
        grouped_chunks: dict[str, list[tuple[ChunkRecord, float]]] = {}
        for chunk, score in hits:
            adjusted_score = score + self._score_boost(question, chunk)
            grouped_scores[chunk.source_id] = max(
                grouped_scores.get(chunk.source_id, float("-inf")),
                adjusted_score,
            )
            grouped_chunks.setdefault(chunk.source_id, []).append((chunk, adjusted_score))

        source_id = max(grouped_scores, key=grouped_scores.get)
        grouped_chunks[source_id].sort(key=lambda item: item[1], reverse=True)
        seed_indexes = {chunk.chunk_index for chunk, _ in grouped_chunks[source_id][:4]}
        context_chunks = self._repository.expand_source_context(source_id, seed_indexes)
        if not context_chunks:
            return None

        primary_chunk = grouped_chunks[source_id][0][0]
        citation = Citation(
            title=primary_chunk.source_title,
            url=primary_chunk.source_url,
            publisher=primary_chunk.authority.upper(),
            document_type=primary_chunk.document_type,
            updated_at=primary_chunk.published_at or "Last successful ingest",
        )
        context = "\n\n".join(chunk.text for chunk in context_chunks)
        return RetrievedSource(citation=citation, context=context)

    def _score_boost(self, question: str, chunk: ChunkRecord) -> float:
        lowered_question = question.lower()
        boost = 0.0

        exact_scheme_matches = [
            scheme_name for scheme_name in chunk.scheme_names if scheme_name.lower() in lowered_question
        ]
        if exact_scheme_matches:
            boost += 7.0 if len(chunk.scheme_names) == 1 else 2.5

        if PROCESS_PATTERN.search(lowered_question):
            if chunk.document_type in PROCESS_TYPES:
                boost += 8.0
            elif chunk.document_type in SCHEME_FACT_TYPES:
                boost -= 3.0
            if chunk.source_id == "groww-home":
                boost += 3.0

        if EXPENSE_PATTERN.search(lowered_question):
            if chunk.document_type == "ter_notice":
                boost += 9.0
            elif chunk.document_type == "factsheet":
                boost += 6.0
            elif chunk.document_type == "ter_reference":
                boost += 4.0
            elif chunk.document_type in {"kim", "sid"}:
                boost -= 1.0

        if SCHEME_FACT_PATTERN.search(lowered_question):
            if chunk.document_type in {"kim", "sid"}:
                boost += 5.0
            elif chunk.document_type == "factsheet":
                boost += 3.0

        if FUND_MANAGER_PATTERN.search(lowered_question):
            if chunk.document_type == "factsheet":
                boost += 7.0
            elif chunk.document_type in {"kim", "sid"}:
                boost += 4.0

        return boost
