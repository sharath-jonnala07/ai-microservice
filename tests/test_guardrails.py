from app.services.guardrails import QuestionIntent, detect_pii, evaluate_question


def test_detect_pan_as_pii() -> None:
    findings = detect_pii("My PAN is ABCDE1234F")
    assert "pan" in findings


def test_advice_is_refused() -> None:
    decision = evaluate_question("Should I buy this mutual fund right now?")
    assert decision.block is True
    assert decision.intent == QuestionIntent.ADVICE


def test_fact_question_is_allowed() -> None:
    decision = evaluate_question("What is the expense ratio of the scheme?")
    assert decision.block is False
    assert decision.intent == QuestionIntent.FACTUAL
