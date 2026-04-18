from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum


class QuestionIntent(StrEnum):
    FACTUAL = "factual"
    PROCESS = "process"
    ADVICE = "advice"
    PERFORMANCE = "performance"
    COMPARISON = "comparison"
    PII = "pii"
    UNSUPPORTED = "unsupported"


@dataclass(slots=True)
class GuardrailDecision:
    intent: QuestionIntent
    block: bool
    reason: str | None = None
    pii_matches: list[str] = field(default_factory=list)


PAN_PATTERN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
AADHAAR_PATTERN = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?:\+91[-\s]?)?[6-9]\d{9}\b")
OTP_PATTERN = re.compile(r"\botp\b|\bone[-\s]?time password\b", re.IGNORECASE)
ACCOUNT_PATTERN = re.compile(r"\b(?:account|folio|ifsc|iban)\b", re.IGNORECASE)

ADVICE_TERMS = (
    "should i invest",
    "should i buy",
    "should i sell",
    "best fund",
    "recommend",
    "worth investing",
    "good fund",
    "which fund should",
)
PERFORMANCE_TERMS = ("returns", "outperform", "cagr", "xirr", "performance", "alpha")
COMPARISON_TERMS = ("compare", "better than", "vs", "versus", "top fund")
PROCESS_TERMS = ("download", "statement", "capital gains", "tax", "account statement")
FACTUAL_TERMS = (
    "expense ratio",
    "exit load",
    "minimum sip",
    "sip",
    "lock-in",
    "lock in",
    "benchmark",
    "riskometer",
    "scheme",
    "fund",
)


def evaluate_question(question: str) -> GuardrailDecision:
    lowered = question.lower()
    pii_matches = detect_pii(question)
    if pii_matches:
        return GuardrailDecision(
            intent=QuestionIntent.PII,
            block=True,
            reason="personal_data",
            pii_matches=pii_matches,
        )
    if any(term in lowered for term in ADVICE_TERMS):
        return GuardrailDecision(QuestionIntent.ADVICE, True, "investment_advice")
    if any(term in lowered for term in PERFORMANCE_TERMS):
        return GuardrailDecision(QuestionIntent.PERFORMANCE, True, "performance_claims")
    if any(term in lowered for term in COMPARISON_TERMS):
        return GuardrailDecision(QuestionIntent.COMPARISON, True, "comparative_judgement")
    if any(term in lowered for term in PROCESS_TERMS):
        return GuardrailDecision(QuestionIntent.PROCESS, False)
    if any(term in lowered for term in FACTUAL_TERMS):
        return GuardrailDecision(QuestionIntent.FACTUAL, False)
    return GuardrailDecision(QuestionIntent.UNSUPPORTED, True, "unsupported_query")


def detect_pii(text: str) -> list[str]:
    findings: list[str] = []
    patterns = {
        "pan": PAN_PATTERN,
        "aadhaar": AADHAAR_PATTERN,
        "email": EMAIL_PATTERN,
        "phone": PHONE_PATTERN,
        "otp": OTP_PATTERN,
        "account": ACCOUNT_PATTERN,
    }
    for label, pattern in patterns.items():
        if pattern.search(text):
            findings.append(label)
    return findings
