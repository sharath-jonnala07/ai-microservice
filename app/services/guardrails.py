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
    CONVERSATIONAL = "conversational"
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
ACCOUNT_PATTERN = re.compile(r"\b(?:account\s*(?:number|no\.?|num)|folio|ifsc|iban)\b", re.IGNORECASE)

ADVICE_TERMS = (
    "should i invest",
    "should i buy",
    "should i sell",
    "best fund",
    "best for me",
    "which is best",
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
    "ter",
    "total expense ratio",
    "exit load",
    "redemption load",
    "minimum sip",
    "min sip",
    "sip",
    "lock-in",
    "lock in",
    "lockin",
    "benchmark",
    "riskometer",
    "risk-o-meter",
    "risk level",
    "scheme",
    "fund",
    "fund manager",
    "portfolio manager",
    "managed by",
    "who manages",
    "investment objective",
    "fund type",
    "fund category",
    "nav",
    "net asset value",
    "aum",
    "assets under management",
    "fund size",
    "minimum investment",
    "minimum lumpsum",
    "plans and options",
    "direct plan",
    "regular plan",
    "growth option",
    "idcw",
    "registrar",
    "transfer agent",
    "grievance",
    "large cap",
    "elss",
    "tax saver",
    "banking",
    "financial services",
    "nifty 50",
    "nifty50",
    "index fund",
    "groww",
    "er",
    "charges",
    "fees",
    "exit",
    "load",
    "min",
    "max",
    "minimum",
    "maximum",
    "risk",
    "safe",
    "manager",
    "objective",
    "plans",
    "options",
    "statement",
    "capital gains",
    "tax",
    "cas",
    "download",
)

# Recognized Groww scheme names — questions mentioning any of these always pass through
SCHEME_NAME_TERMS = (
    "groww large cap",
    "groww elss",
    "groww tax saver",
    "groww banking",
    "groww financial services",
    "groww nifty",
    "groww nifty 50",
    "large cap fund",
    "elss tax saver",
    "banking and financial",
    "nifty 50 index",
    "groww mutual fund",
    "groww mf",
    "groww amc",
)

# Conversational / greeting patterns — these are NOT blocked
GREETING_PATTERNS = re.compile(
    r"^\s*("
    r"h(i|ello|ey|owdy|ola)"
    r"|good\s*(morning|afternoon|evening|day|night)"
    r"|what'?s?\s*up"
    r"|yo\b"
    r"|sup\b"
    r"|namaste"
    r"|thanks?(\s+you)?(\s+so\s+much)?"
    r"|thank\s+you"
    r"|bye\b"
    r"|goodbye"
    r"|see\s+you"
    r"|take\s+care"
    r"|who\s+are\s+you"
    r"|what\s+(can|do)\s+you\s+do"
    r"|help\s*$"
    r"|help\s+me"
    r"|how\s+are\s+you"
    r"|what\s+is\s+this"
    r"|tell\s+me\s+about\s+yourself"
    r")\s*[?!.]*\s*$",
    re.IGNORECASE,
)

CONVERSATIONAL_RESPONSES: dict[str, str] = {
    "greeting": (
        "Hey there! 👋 I'm FundIntel, your AI assistant for Groww Mutual Fund questions. "
        "I can help you with expense ratios, exit loads, SIP minimums, lock-in periods, "
        "benchmarks, fund managers, and more — all backed by official sources.\n\n"
        "Try asking something like:\n"
        "• What is the expense ratio of Groww Large Cap Fund?\n"
        "• What's the minimum SIP for Groww Nifty 50 Index Fund?\n"
        "• What is the lock-in period for Groww ELSS Tax Saver Fund?"
    ),
    "thanks": (
        "You're welcome! Feel free to ask anything else about Groww Mutual Funds. "
        "I'm here to help with verified facts from official sources. 😊"
    ),
    "farewell": (
        "Goodbye! Feel free to come back anytime you have questions about "
        "Groww Mutual Funds. Have a great day! 👋"
    ),
    "identity": (
        "I'm FundIntel — an AI assistant specializing in Groww Mutual Fund information. "
        "I provide fact-checked answers sourced from official AMC, SEBI, and AMFI documents. "
        "Ask me about expense ratios, exit loads, SIP minimums, lock-in periods, benchmarks, "
        "fund managers, riskometer levels, and more!"
    ),
    "help": (
        "I can help you with factual information about Groww Mutual Fund schemes:\n\n"
        "📊 **Expense ratios** — e.g. \"What's the TER of Groww Large Cap Fund?\"\n"
        "🔒 **Lock-in periods** — e.g. \"Lock-in for Groww ELSS?\"\n"
        "💰 **SIP minimums** — e.g. \"Min SIP for Groww Nifty 50?\"\n"
        "📈 **Benchmarks** — e.g. \"Benchmark of Groww Banking Fund?\"\n"
        "🛡️ **Risk levels** — e.g. \"Riskometer of Groww Large Cap?\"\n"
        "👤 **Fund managers** — e.g. \"Who manages Groww ELSS?\"\n"
        "📄 **Statements** — e.g. \"How to download capital gains statement?\"\n\n"
        "Just ask naturally — I understand casual phrasing too!"
    ),
}


def _detect_conversational_subtype(lowered: str) -> str | None:
    """Return the conversational sub-type key, or None."""
    if re.search(r"\b(thank|thanks)\b", lowered):
        return "thanks"
    if re.search(r"\b(bye|goodbye|see\s+you|take\s+care)\b", lowered):
        return "farewell"
    if re.search(r"\b(who\s+are\s+you|what\s+(can|do)\s+you|tell\s+me\s+about\s+yourself|what\s+is\s+this)\b", lowered):
        return "identity"
    if re.search(r"\bhelp\b", lowered):
        return "help"
    return "greeting"


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
    # Conversational — greetings, thanks, help (NOT blocked)
    if GREETING_PATTERNS.match(lowered):
        subtype = _detect_conversational_subtype(lowered)
        return GuardrailDecision(QuestionIntent.CONVERSATIONAL, False, subtype)
    if any(term in lowered for term in PROCESS_TERMS):
        return GuardrailDecision(QuestionIntent.PROCESS, False)
    if any(term in lowered for term in FACTUAL_TERMS):
        return GuardrailDecision(QuestionIntent.FACTUAL, False)
    if any(term in lowered for term in SCHEME_NAME_TERMS):
        return GuardrailDecision(QuestionIntent.FACTUAL, False)
    # Default: ALLOW through to RAG pipeline (not block)
    # The LLM + retrieval pipeline will handle unknown queries gracefully
    return GuardrailDecision(QuestionIntent.FACTUAL, False)


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
