from __future__ import annotations

from io import BytesIO

import httpx
import trafilatura
from pypdf import PdfReader

from app.models.schemas import SourceRecord


def fetch_source_text(source: SourceRecord, user_agent: str, timeout_seconds: int) -> str:
    headers = {"User-Agent": user_agent}
    with httpx.Client(timeout=timeout_seconds, follow_redirects=True, headers=headers) as client:
        response = client.get(str(source.url))
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "pdf" in content_type or str(source.url).lower().endswith(".pdf"):
            return _extract_pdf_text(response.content)
        return _extract_html_text(response.text)


def _extract_html_text(html: str) -> str:
    extracted = trafilatura.extract(html, include_links=False, include_tables=False)
    return extracted or ""


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    return "\n".join((page.extract_text() or "") for page in reader.pages)
