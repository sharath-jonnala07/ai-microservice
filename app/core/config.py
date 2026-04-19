from __future__ import annotations

from typing import Annotated
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "FundIntel Mutual Fund RAG"
    environment: str = "development"
    api_prefix: str = "/v1"
    log_level: str = "INFO"
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    groq_api_key: SecretStr | None = None
    groq_model: str = "llama-3.1-8b-instant"
    embeddings_model: str = "BAAI/bge-small-en-v1.5"
    request_timeout_seconds: int = 20
    retrieval_k: int = 8
    max_answer_sentences: int = 5
    source_manifest_path: Path = BASE_DIR / "data" / "sources" / "groww_sources.json"
    vector_index_path: Path = BASE_DIR / "data" / "index" / "faiss"
    chunk_store_path: Path = BASE_DIR / "data" / "index" / "chunks.json"
    user_agent: str = "FundIntelBot/1.0"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> list[str]:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    @field_validator("api_prefix")
    @classmethod
    def normalize_api_prefix(cls, value: str) -> str:
        return value if value.startswith("/") else f"/{value}"

    @model_validator(mode="after")
    def normalize_paths(self) -> "Settings":
        for field_name in ("source_manifest_path", "vector_index_path", "chunk_store_path"):
            path_value = getattr(self, field_name)
            if not path_value.is_absolute():
                setattr(self, field_name, BASE_DIR / path_value)
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
