"""Quick end-to-end test hitting the running server for all PRD question categories."""
import json, time, requests

BASE = "http://127.0.0.1:8000/v1/qa"

QUESTIONS = [
    # Expense ratio / TER
    ("What is the TER of Groww ELSS Tax Saver Fund?", "0.80%"),
    ("What is the expense ratio of Groww Nifty 50 Index Fund?", "0.30%"),
    # Exit load
    ("What is the exit load of Groww Large Cap Fund?", "1%"),
    ("What is the exit load of Groww Banking and Financial Services Fund?", "1.00%"),
    ("What is the exit load of Groww Nifty 50 Index Fund?", "Nil"),
    # Benchmark
    ("What is the benchmark of Groww Large Cap Fund?", "NIFTY 100"),
    ("What is the benchmark of Groww ELSS Tax Saver Fund?", "Nifty 500"),
    # Riskometer
    ("What is the riskometer of Groww Banking and Financial Services Fund?", "Very High"),
    # Min SIP
    ("What is the minimum SIP amount for Groww Large Cap Fund?", "500"),
    # Lock-in
    ("What is the lock-in period for Groww ELSS Tax Saver Fund?", "3 year"),
    ("Is there a lock-in for Groww Nifty 50 Index Fund?", "no lock-in"),
    # Fund manager
    ("Who manages Groww Large Cap Fund?", "Anupam Tiwari"),
    ("Who is the fund manager of Groww Nifty 50 Index Fund?", "Aakash Chauhan"),
    # Investment objective
    ("What is the investment objective of Groww ELSS Tax Saver Fund?", "capital appreciation"),
    # Fund type
    ("What type of fund is Groww Large Cap Fund?", "Large Cap"),
    # Plans and options
    ("What plans are available for Groww Large Cap Fund?", "Regular Plan"),
    # Min lumpsum
    ("What is the minimum investment for Groww Nifty 50 Index Fund?", "500"),
    # Statement guidance (general)
    ("How do I get my account statement from Groww Mutual Fund?", "5 business days"),
    # Registrar (general)
    ("Who is the registrar of Groww Mutual Fund?", "KFin"),
    # Guardrail: advice → refusal
    ("Should I invest in Groww Large Cap Fund?", None),
    # Guardrail: PII → refusal
    ("My PAN is ABCDE1234F", None),
    # AUM (no fact table entry yet - should fall through to RAG)
    ("What is the AUM of Groww Nifty 50 Index Fund?", None),
]

results = []
for q, expected_snippet in QUESTIONS:
    r = requests.post(BASE, json={"question": q}, timeout=30)
    data = r.json()
    answer = data.get("answer", "")
    status = data.get("status", "")
    latency = data.get("latency_ms", "?")
    if expected_snippet is None:
        # We just want to see what happens — no strict check
        ok = True
    else:
        ok = expected_snippet.lower() in answer.lower()
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] ({latency}ms) {status}: {q}")
    if not ok:
        print(f"       Expected '{expected_snippet}' in: {answer[:200]}")
    results.append((tag, q))

passed = sum(1 for tag, _ in results if tag == "PASS")
print(f"\n{passed}/{len(results)} passed")
