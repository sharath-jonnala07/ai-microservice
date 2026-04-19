"""Question classifier — maps user questions to (scheme_name, fact_type) tuples."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class Classification:
    scheme: str | None
    fact_type: str | None


# ---------------------------------------------------------------------------
# Scheme aliases  (lowercased)
# ---------------------------------------------------------------------------
SCHEME_ALIASES: dict[str, str] = {
    # Groww Large Cap Fund
    "groww large cap fund": "Groww Large Cap Fund",
    "large cap fund": "Groww Large Cap Fund",
    "large cap": "Groww Large Cap Fund",
    "largecap": "Groww Large Cap Fund",
    "large-cap": "Groww Large Cap Fund",
    # Groww ELSS Tax Saver Fund
    "groww elss tax saver fund": "Groww ELSS Tax Saver Fund",
    "elss tax saver fund": "Groww ELSS Tax Saver Fund",
    "elss tax saver": "Groww ELSS Tax Saver Fund",
    "elss fund": "Groww ELSS Tax Saver Fund",
    "elss": "Groww ELSS Tax Saver Fund",
    "tax saver fund": "Groww ELSS Tax Saver Fund",
    "tax saver": "Groww ELSS Tax Saver Fund",
    # Groww Banking and Financial Services Fund
    "groww banking and financial services fund": "Groww Banking and Financial Services Fund",
    "groww banking & financial services fund": "Groww Banking and Financial Services Fund",
    "banking and financial services fund": "Groww Banking and Financial Services Fund",
    "banking & financial services fund": "Groww Banking and Financial Services Fund",
    "banking fund": "Groww Banking and Financial Services Fund",
    "banking and financial services": "Groww Banking and Financial Services Fund",
    "banking & financial services": "Groww Banking and Financial Services Fund",
    "financial services fund": "Groww Banking and Financial Services Fund",
    "bfsi fund": "Groww Banking and Financial Services Fund",
    "bfsi": "Groww Banking and Financial Services Fund",
    # Groww Nifty 50 Index Fund
    "groww nifty 50 index fund": "Groww Nifty 50 Index Fund",
    "nifty 50 index fund": "Groww Nifty 50 Index Fund",
    "nifty 50 fund": "Groww Nifty 50 Index Fund",
    "nifty 50": "Groww Nifty 50 Index Fund",
    "nifty50": "Groww Nifty 50 Index Fund",
    "index fund": "Groww Nifty 50 Index Fund",
}

# Sort by longest first so "groww large cap fund" matches before "large cap"
_SORTED_SCHEME_ALIASES = sorted(SCHEME_ALIASES.keys(), key=len, reverse=True)


# ---------------------------------------------------------------------------
# Fact-type keyword map  (lowercased trigger → fact_type key)
# ---------------------------------------------------------------------------
FACT_TYPE_KEYWORDS: dict[str, str] = {
    # expense_ratio
    "expense ratio": "expense_ratio",
    "ter": "expense_ratio",
    "total expense ratio": "expense_ratio",
    "total expense": "expense_ratio",
    "management fee": "expense_ratio",
    "management fees": "expense_ratio",
    "annual charge": "expense_ratio",
    "annual charges": "expense_ratio",
    "recurring expense": "expense_ratio",
    "er": "expense_ratio",
    "charges": "expense_ratio",
    "fees": "expense_ratio",
    # exit_load
    "exit load": "exit_load",
    "exit fee": "exit_load",
    "redemption load": "exit_load",
    "redemption fee": "exit_load",
    "redemption charge": "exit_load",
    "withdrawal charge": "exit_load",
    "early exit": "exit_load",
    # benchmark
    "benchmark": "benchmark",
    "benchmark index": "benchmark",
    "tracks which index": "benchmark",
    # riskometer
    "riskometer": "riskometer",
    "risk-o-meter": "riskometer",
    "risk level": "riskometer",
    "risk category": "riskometer",
    "risk rating": "riskometer",
    "how risky": "riskometer",
    "risk grade": "riskometer",
    "how safe": "riskometer",
    # min_sip
    "minimum sip": "min_sip",
    "min sip": "min_sip",
    "sip amount": "min_sip",
    "sip minimum": "min_sip",
    "minimum sip amount": "min_sip",
    "sip investment": "min_sip",
    "monthly sip": "min_sip",
    "sip start": "min_sip",
    # lock_in
    "lock-in": "lock_in",
    "lock in": "lock_in",
    "lockin": "lock_in",
    "lock-in period": "lock_in",
    "lock in period": "lock_in",
    # fund_manager
    "fund manager": "fund_manager",
    "portfolio manager": "fund_manager",
    "managed by": "fund_manager",
    "who manages": "fund_manager",
    "manager of": "fund_manager",
    # investment_objective
    "investment objective": "investment_objective",
    "scheme objective": "investment_objective",
    "fund objective": "investment_objective",
    "objective of": "investment_objective",
    "what does the fund invest in": "investment_objective",
    "investment goal": "investment_objective",
    # fund_type
    "fund type": "fund_type",
    "scheme type": "fund_type",
    "type of fund": "fund_type",
    "type of scheme": "fund_type",
    "category of fund": "fund_type",
    "fund category": "fund_type",
    "what type": "fund_type",
    "what kind": "fund_type",
    # min_lumpsum
    "minimum investment": "min_lumpsum",
    "minimum lumpsum": "min_lumpsum",
    "min investment": "min_lumpsum",
    "minimum purchase": "min_lumpsum",
    "minimum application": "min_lumpsum",
    "min lumpsum": "min_lumpsum",
    "minimum amount": "min_lumpsum",
    # plans_options
    "plans and options": "plans_options",
    "plan and option": "plans_options",
    "plans available": "plans_options",
    "plans are available": "plans_options",
    "what plans": "plans_options",
    "which plans": "plans_options",
    "growth option": "plans_options",
    "idcw option": "plans_options",
    "dividend option": "plans_options",
    "direct plan": "plans_options",
    "regular plan": "plans_options",
    # aum
    "aum": "aum",
    "assets under management": "aum",
    "corpus size": "aum",
    "fund size": "aum",
    "net assets": "aum",
    # nav
    "nav": "nav",
    "net asset value": "nav",
    "current nav": "nav",
    # statement / CAS
    "account statement": "statement_guidance",
    "consolidated account statement": "statement_guidance",
    "capital gains statement": "statement_guidance",
    "capital gain statement": "statement_guidance",
    "download statement": "statement_guidance",
    "cas statement": "statement_guidance",
    "how to get statement": "statement_guidance",
    "tax statement": "statement_guidance",
    # registrar
    "registrar": "registrar",
    "rta": "registrar",
    "transfer agent": "registrar",
}

# Sort by longest first
_SORTED_FACT_KEYWORDS = sorted(FACT_TYPE_KEYWORDS.keys(), key=len, reverse=True)


# ---------------------------------------------------------------------------
# Synonym expansion map for retrieval  (lowercased)
# ---------------------------------------------------------------------------
SYNONYMS: dict[str, list[str]] = {
    "ter": ["total expense ratio", "expense ratio"],
    "total expense ratio": ["ter", "expense ratio"],
    "expense ratio": ["ter", "total expense ratio"],
    "nav": ["net asset value"],
    "net asset value": ["nav"],
    "aum": ["assets under management", "fund size"],
    "assets under management": ["aum", "fund size"],
    "fund size": ["aum", "assets under management"],
    "idcw": ["dividend", "income distribution"],
    "dividend": ["idcw", "income distribution"],
    "sip": ["systematic investment plan"],
    "systematic investment plan": ["sip"],
    "lock-in": ["lock in", "lockin"],
    "lock in": ["lock-in", "lockin"],
    "exit load": ["redemption load", "exit fee"],
    "riskometer": ["risk-o-meter", "risk level"],
    "cas": ["consolidated account statement"],
    "benchmark": ["benchmark index"],
}


def classify_question(question: str) -> Classification:
    """Classify a question into (scheme_name, fact_type)."""
    lowered = question.lower()

    # Detect scheme
    scheme: str | None = None
    for alias in _SORTED_SCHEME_ALIASES:
        if alias in lowered:
            scheme = SCHEME_ALIASES[alias]
            break

    # Detect fact type
    fact_type: str | None = None
    for keyword in _SORTED_FACT_KEYWORDS:
        if keyword in lowered:
            fact_type = FACT_TYPE_KEYWORDS[keyword]
            break

    # Fallback: if "sip" appears alone, map to min_sip
    if fact_type is None and re.search(r"\bsip\b", lowered):
        fact_type = "min_sip"

    return Classification(scheme=scheme, fact_type=fact_type)


def expand_query_with_synonyms(question: str) -> str:
    """Expand the query with synonym terms for better lexical matching."""
    lowered = question.lower()
    expansions: list[str] = []
    for term, synonyms in SYNONYMS.items():
        if term in lowered:
            for syn in synonyms:
                if syn not in lowered:
                    expansions.append(syn)
    if not expansions:
        return question
    return question + " " + " ".join(expansions)
