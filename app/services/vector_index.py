from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from hashlib import blake2b

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.core.config import Settings
from app.models.schemas import ChunkRecord


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")


class LocalHashEmbeddings(Embeddings):
    def __init__(self, dimensions: int = 256) -> None:
        self._dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_text(text)

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for token in _tokenize(text):
            digest = blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:8], byteorder="big") % self._dimensions
            sign = 1.0 if digest[8] % 2 == 0 else -1.0
            weight = 1.0 + (digest[9] / 255.0)
            vector[index] += sign * weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class VectorIndexRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._embeddings: Embeddings | None = None
        self._vectorstore: FAISS | None = None
        self._chunks: list[ChunkRecord] = []
        self._chunks_by_id: dict[str, ChunkRecord] = {}
        self._chunks_by_source: dict[str, list[ChunkRecord]] = defaultdict(list)

    def is_ready(self) -> bool:
        return self._vectorstore is not None and bool(self._chunks)

    def index_files_exist(self) -> bool:
        return self._settings.vector_index_path.exists() and self._settings.chunk_store_path.exists()

    def load(self) -> bool:
        if not self.index_files_exist():
            return False
        self._vectorstore = FAISS.load_local(
            str(self._settings.vector_index_path),
            self._get_embeddings(),
            allow_dangerous_deserialization=True,
        )
        chunk_data = json.loads(self._settings.chunk_store_path.read_text(encoding="utf-8"))
        self._chunks = [ChunkRecord.model_validate(item) for item in chunk_data]
        self._chunks_by_id = {item.chunk_id: item for item in self._chunks}
        self._chunks_by_source = defaultdict(list)
        for chunk in self._chunks:
            self._chunks_by_source[chunk.source_id].append(chunk)
        for source_chunks in self._chunks_by_source.values():
            source_chunks.sort(key=lambda item: item.chunk_index)
        return True

    def build(self, chunks: list[ChunkRecord]) -> None:
        documents = [
            Document(page_content=chunk.text, metadata=chunk.model_dump(mode="json"))
            for chunk in chunks
        ]
        self._settings.vector_index_path.parent.mkdir(parents=True, exist_ok=True)
        vectorstore = FAISS.from_documents(documents, self._get_embeddings())
        vectorstore.save_local(str(self._settings.vector_index_path))
        self._settings.chunk_store_path.write_text(
            json.dumps([chunk.model_dump(mode="json") for chunk in chunks], indent=2),
            encoding="utf-8",
        )
        self._vectorstore = vectorstore
        self._chunks = chunks
        self._chunks_by_id = {item.chunk_id: item for item in chunks}
        self._chunks_by_source = defaultdict(list)
        for chunk in chunks:
            self._chunks_by_source[chunk.source_id].append(chunk)
        for source_chunks in self._chunks_by_source.values():
            source_chunks.sort(key=lambda item: item.chunk_index)

    def search(self, question: str, k: int) -> list[tuple[ChunkRecord, float]]:
        if self._vectorstore is None:
            return []

        combined_scores: dict[str, float] = defaultdict(float)

        for document, raw_score in self._vectorstore.similarity_search_with_score(question, k=k):
            chunk_id = document.metadata["chunk_id"]
            combined_scores[chunk_id] += 1 / (1 + float(raw_score))

        lexical_scores = self._lexical_scores(question)
        for chunk_id, lexical_score in lexical_scores.items():
            combined_scores[chunk_id] += lexical_score

        ranked = sorted(
            ((self._chunks_by_id[chunk_id], score) for chunk_id, score in combined_scores.items()),
            key=lambda item: item[1],
            reverse=True,
        )
        return ranked[:k]

    def expand_source_context(self, source_id: str, seed_indexes: set[int], radius: int = 1) -> list[ChunkRecord]:
        source_chunks = self._chunks_by_source.get(source_id, [])
        if not source_chunks:
            return []
        included_indexes: set[int] = set()
        for index in seed_indexes:
            for candidate_index in range(max(index - radius, 0), index + radius + 1):
                included_indexes.add(candidate_index)
        return [chunk for chunk in source_chunks if chunk.chunk_index in included_indexes]

    def indexed_source_count(self) -> int:
        return len(self._chunks_by_source)

    def all_chunks(self) -> list[ChunkRecord]:
        return self._chunks

    def _get_embeddings(self) -> Embeddings:
        if self._embeddings is None:
            self._embeddings = LocalHashEmbeddings()
        return self._embeddings

    def _lexical_scores(self, question: str) -> dict[str, float]:
        question_tokens = set(_tokenize(question))
        if not question_tokens:
            return {}
        scores: dict[str, float] = {}
        for chunk in self._chunks:
            chunk_tokens = set(_tokenize(chunk.text))
            if not chunk_tokens:
                continue
            overlap = len(question_tokens & chunk_tokens)
            if overlap == 0:
                continue
            scores[chunk.chunk_id] = overlap / math.sqrt(len(chunk_tokens))
        return scores


def _tokenize(value: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(value)]
