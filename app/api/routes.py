from __future__ import annotations

import time

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import ORJSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.core.telemetry import CHAT_LATENCY_SECONDS
from app.models.schemas import ChatRequest, ChatResponse, HealthResponse


router = APIRouter()


@router.post("/qa", response_model=ChatResponse)
async def answer_question(payload: ChatRequest, request: Request) -> ORJSONResponse:
    qa_service = request.app.state.qa_service
    with CHAT_LATENCY_SECONDS.time():
        result = await qa_service.answer(payload)
    status_code = status.HTTP_200_OK if result.status != "error" else status.HTTP_503_SERVICE_UNAVAILABLE
    return ORJSONResponse(status_code=status_code, content=result.model_dump(mode="json"))


@router.get("/health/live", response_model=HealthResponse)
async def liveness(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    qa_service = request.app.state.qa_service
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        indexed_sources=qa_service.indexed_source_count(),
        groq_configured=qa_service.groq_configured(),
    )


@router.get("/health/ready", response_model=HealthResponse)
async def readiness(request: Request, response: Response) -> HealthResponse:
    settings = request.app.state.settings
    qa_service = request.app.state.qa_service
    ready = qa_service.ready()
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="ok" if ready else "degraded",
        environment=settings.environment,
        indexed_sources=qa_service.indexed_source_count(),
        groq_configured=qa_service.groq_configured(),
    )


@router.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
