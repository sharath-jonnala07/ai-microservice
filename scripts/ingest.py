from __future__ import annotations

from app.core.config import get_settings
from app.ingestion.pipeline import run_ingestion


def main() -> None:
    settings = get_settings()
    count = run_ingestion(settings)
    print(f"Indexed {count} chunks from the configured official sources.")


if __name__ == "__main__":
    main()
