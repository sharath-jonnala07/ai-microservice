from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import Settings
from app.core.telemetry import CHAT_REQUESTS, RETRIEVAL_MISSES
from app.models.schemas import ChatRequest, ChatResponse, Citation, SourceRecord
from app.services.fact_lookup import FactLookupService
from app.services.guardrails import CONVERSATIONAL_RESPONSES, QuestionIntent, evaluate_question
from app.services.prompts import REFUSAL_COPY, SYSTEM_PROMPT
from app.services.question_classifier import classify_question
from app.services.retrieval import SourceRetriever
from app.services.source_manifest import load_source_manifest
from app.services.vector_index import VectorIndexRepository


LOGGER = logging.getLogger(__name__)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
NAMED_SCHEME_PATTERN = re.compile(r"\b([A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*)*\s+(?:Fund|ETF|FOF))\b")


class QAService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._repository = VectorIndexRepository(settings)
        self._retriever = SourceRetriever(self._repository, settings)
        self._fact_lookup = FactLookupService()
        self._sources = {source.source_id: source for source in load_source_manifest(settings.source_manifest_path)}
        self._supported_scheme_names = {
            scheme_name.lower()
            for source in self._sources.values()
            for scheme_name in source.scheme_names
        }
        self._llm: Any | None = None
        self._repository_load_attempted = False
        self._repository_lock = asyncio.Lock()

    def indexed_source_count(self) -> int:
        if not self._repository.is_ready() and self._repository.index_files_exist():
            return len(self._sources)
        return self._repository.indexed_source_count()

    def groq_configured(self) -> bool:
        return self._settings.groq_api_key is not None

    def ready(self) -> bool:
        return self._repository.index_files_exist() and self.groq_dependency_available() and self.groq_configured()

    def groq_dependency_available(self) -> bool:
        if self._llm is not None:
            return True
        try:
            self._import_chat_groq()
        except ModuleNotFoundError as error:
            LOGGER.warning("langchain_groq is not installed: %s", error)
            return False
        return True

    async def answer(self, payload: ChatRequest) -> ChatResponse:
        start = time.perf_counter()
        decision = evaluate_question(payload.question)
        if decision.block:
            response = self._build_refusal(decision.reason or "unsupported_query")
            response.latency_ms = int((time.perf_counter() - start) * 1000)
            CHAT_REQUESTS.labels(status=response.status).inc()
            return response

        # Handle conversational queries (greetings, thanks, help) without RAG
        if decision.intent == QuestionIntent.CONVERSATIONAL:
            subtype = decision.reason or "greeting"
            answer_text = CONVERSATIONAL_RESPONSES.get(subtype, CONVERSATIONAL_RESPONSES["greeting"])
            response = ChatResponse(
                status="answer",
                answer=answer_text,
                last_updated_from_sources="N/A — conversational response",
            )
            response.latency_ms = int((time.perf_counter() - start) * 1000)
            CHAT_REQUESTS.labels(status=response.status).inc()
            return response

        # Prefer deterministic fact-table answers before requiring Groq or the vector index.
        rule_based_response = self._try_fact_table(payload.question)
        if rule_based_response is not None:
            rule_based_response.latency_ms = int((time.perf_counter() - start) * 1000)
            CHAT_REQUESTS.labels(status=rule_based_response.status).inc()
            return rule_based_response

        if not self._settings.groq_api_key:
            response = ChatResponse(
                status="error",
                answer="The assistant is not configured yet. Add a Groq API key to enable live answers.",
                last_updated_from_sources="Unavailable",
                error_code="groq_api_key_missing",
            )
            response.latency_ms = int((time.perf_counter() - start) * 1000)
            CHAT_REQUESTS.labels(status=response.status).inc()
            return response

        if not self.groq_dependency_available():
            response = ChatResponse(
                status="error",
                answer="The assistant backend is missing the Groq integration package. Install backend dependencies and restart the service.",
                last_updated_from_sources="Unavailable",
                error_code="groq_dependency_missing",
            )
            response.latency_ms = int((time.perf_counter() - start) * 1000)
            CHAT_REQUESTS.labels(status=response.status).inc()
            return response

        await self._ensure_repository_loaded()
        if not self._repository.is_ready():
            response = ChatResponse(
                status="error",
                answer="The assistant has no indexed official source corpus yet. Run ingestion and add verified Groww, AMFI, and SEBI sources before asking factual questions.",
                last_updated_from_sources="Unavailable",
                error_code="corpus_not_indexed",
            )
            response.latency_ms = int((time.perf_counter() - start) * 1000)
            CHAT_REQUESTS.labels(status=response.status).inc()
            return response

        if not self._is_general_groww_query(payload.question) and self._question_has_out_of_scope_scheme(payload.question):
            response = ChatResponse(
                status="insufficient_data",
                answer="I could not verify that because the current corpus is limited to the indexed Groww schemes only. Please ask about Groww Large Cap Fund, Groww ELSS Tax Saver Fund, Groww Banking and Financial Services Fund, or Groww Nifty 50 Index Fund.",
                citation=self._fallback_citation(QuestionIntent.UNSUPPORTED),
                last_updated_from_sources="Last updated from sources: current corpus limited to supported Groww schemes",
                refusal_reason="out_of_scope_scheme",
            )
            response.latency_ms = int((time.perf_counter() - start) * 1000)
            CHAT_REQUESTS.labels(status=response.status).inc()
            return response

        retrieved = self._retriever.retrieve(payload.question)
        if retrieved is None:
            RETRIEVAL_MISSES.inc()
            response = ChatResponse(
                status="insufficient_data",
                answer="I could not verify that from the currently indexed official sources. Please try a narrower factual question about scheme fees, lock-in, riskometer, benchmark, or statement guidance.",
                citation=self._fallback_citation(QuestionIntent.UNSUPPORTED),
                last_updated_from_sources="Last updated from sources: current corpus unavailable for this query",
                refusal_reason="unverified_from_corpus",
            )
            response.latency_ms = int((time.perf_counter() - start) * 1000)
            CHAT_REQUESTS.labels(status=response.status).inc()
            return response

        answer_text = await self._generate_answer(payload.question, retrieved.context)
        answer_text = self._sanitize_answer(answer_text)

        response = ChatResponse(
            status="answer",
            answer=answer_text,
            citation=retrieved.citation,
            last_updated_from_sources=f"Last updated from sources: {retrieved.citation.updated_at}",
        )
        response.latency_ms = int((time.perf_counter() - start) * 1000)
        CHAT_REQUESTS.labels(status=response.status).inc()
        return response

    async def _ensure_repository_loaded(self) -> None:
        if self._repository.is_ready() or self._repository_load_attempted:
            return
        async with self._repository_lock:
            if self._repository.is_ready() or self._repository_load_attempted:
                return
            self._repository_load_attempted = True
            await asyncio.to_thread(self._repository.load)

    async def _generate_answer(self, question: str, context: str) -> str:
        llm = self._get_llm()
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                (
                    "human",
                    "Question: {question}\n\nOfficial context:\n{context}\n\nAnswer with only the verified fact.",
                ),
            ]
        )
        chain = prompt | llm | StrOutputParser()
        return await chain.ainvoke({"question": question, "context": context})

    def _get_llm(self) -> Any:
        if self._llm is None:
            chat_groq = self._import_chat_groq()
            self._llm = chat_groq(
                api_key=self._settings.groq_api_key.get_secret_value(),
                model=self._settings.groq_model,
                temperature=0,
                timeout=self._settings.request_timeout_seconds,
            )
        return self._llm

    def _import_chat_groq(self):
        from langchain_groq import ChatGroq

        return ChatGroq

    def _sanitize_answer(self, answer: str) -> str:
        clean = " ".join(answer.strip().split())
        sentences = [segment.strip() for segment in SENTENCE_SPLIT.split(clean) if segment.strip()]
        if not sentences:
            return "I could not verify a concise answer from the current source context."
        trimmed = " ".join(sentences[: self._settings.max_answer_sentences])
        banned_terms = ("should", "recommend", "best option", "buy", "sell")
        if any(term in trimmed.lower() for term in banned_terms):
            return "I can only provide factual information from official sources for this query."
        return trimmed

    def _build_refusal(self, reason: str) -> ChatResponse:
        reason_to_intent = {
            "investment_advice": QuestionIntent.ADVICE,
            "performance_claims": QuestionIntent.PERFORMANCE,
            "comparative_judgement": QuestionIntent.COMPARISON,
            "personal_data": QuestionIntent.PII,
            "unsupported_query": QuestionIntent.UNSUPPORTED,
        }
        intent = reason_to_intent.get(reason, QuestionIntent.UNSUPPORTED)
        citation = self._fallback_citation(intent)
        answer = REFUSAL_COPY.get(reason, REFUSAL_COPY["unsupported_query"])
        return ChatResponse(
            status="refusal",
            answer=answer,
            citation=citation,
            last_updated_from_sources=f"Last updated from sources: {citation.updated_at}",
            refusal_reason=reason,
        )

    def _try_fact_table(self, question: str) -> ChatResponse | None:
        """Tier-1: deterministic lookup from pre-extracted fact table."""
        classification = classify_question(question)
        result = self._fact_lookup.lookup(classification)
        if result is None:
            return None
        citation = Citation(
            title=result.source_title,
            url=result.source_url,
            publisher="GROWW AMC",
            document_type="fact_table",
            updated_at="Pre-verified from official documents",
        )
        return ChatResponse(
            status="answer",
            answer=result.answer,
            citation=citation,
            last_updated_from_sources=f"Last updated from sources: {citation.updated_at}",
        )

    @staticmethod
    def _is_general_groww_query(question: str) -> bool:
        lowered = question.lower()
        return any(term in lowered for term in ("groww mutual fund", "groww mf", "groww amc"))

    def _question_has_out_of_scope_scheme(self, question: str) -> bool:
        lowered = question.lower()
        if any(scheme_name in lowered for scheme_name in self._supported_scheme_names):
            return False
        candidates = [match.group(1).lower() for match in NAMED_SCHEME_PATTERN.finditer(question)]
        return bool(candidates)

    def _fallback_citation(self, intent: QuestionIntent) -> Citation:
        fallback_source: SourceRecord | None = None
        if intent == QuestionIntent.PII:
            fallback_source = self._sources.get("sebi-investor-education")
        elif intent in {QuestionIntent.ADVICE, QuestionIntent.COMPARISON, QuestionIntent.PERFORMANCE}:
            fallback_source = self._sources.get("sebi-investor-education")
        else:
            fallback_source = self._sources.get("amfi-home")

        if fallback_source is None:
            return Citation(
                title="SEBI Investor Education",
                url="https://investor.sebi.gov.in/",
                publisher="SEBI",
                document_type="investor_education",
                updated_at="Official live page",
            )

        return Citation(
            title=fallback_source.title,
            url=fallback_source.url,
            publisher=fallback_source.authority.upper(),
            document_type=fallback_source.document_type,
            updated_at=fallback_source.published_at or "Official live page",
        )
