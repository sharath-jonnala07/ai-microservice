from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter


def create_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=900,
        chunk_overlap=120,
        separators=["\n\n", "\n", ". ", " "],
    )
