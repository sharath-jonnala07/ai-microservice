"""One-time script to extract facts from the indexed corpus chunks."""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
CHUNKS_PATH = BASE / "data" / "index" / "chunks.json"

SCHEMES = [
    "Groww Large Cap Fund",
    "Groww ELSS Tax Saver Fund",
    "Groww Banking and Financial Services Fund",
    "Groww Nifty 50 Index Fund",
]


def load_chunks():
    return json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))


def scheme_chunks(chunks, scheme_name, doc_types=None):
    for c in chunks:
        if scheme_name in c.get("scheme_names", []):
            if doc_types is None or c["document_type"] in doc_types:
                yield c


def search_all(chunks, predicate, doc_types=None):
    for c in chunks:
        if doc_types and c["document_type"] not in doc_types:
            continue
        if predicate(c["text"]):
            yield c


def extract_ter(chunks):
    """Extract TER from ter_notice documents."""
    results = {}
    for scheme in SCHEMES:
        for c in scheme_chunks(chunks, scheme, {"ter_notice"}):
            text = c["text"]
            # Look for percentage patterns near "Regular" and "Direct"
            regular = re.search(r"Regular\s*(?:Plan)?\s*[:\-–]?\s*(\d+\.\d+)%", text, re.IGNORECASE)
            direct = re.search(r"Direct\s*(?:Plan)?\s*[:\-–]?\s*(\d+\.\d+)%", text, re.IGNORECASE)
            if not regular and not direct:
                # Try alternative pattern
                pcts = re.findall(r"(\d+\.\d+)%", text)
                if len(pcts) >= 2:
                    regular_val = pcts[0]
                    direct_val = pcts[1]
                    results[scheme] = {
                        "value": f"Regular Plan: {regular_val}% p.a., Direct Plan: {direct_val}% p.a.",
                        "source_id": c["source_id"],
                        "source_title": c["source_title"],
                        "source_url": c["source_url"],
                        "updated_at": c.get("published_at", ""),
                        "raw": text[:500],
                    }
                    break
            else:
                reg_val = regular.group(1) if regular else "N/A"
                dir_val = direct.group(1) if direct else "N/A"
                results[scheme] = {
                    "value": f"Regular Plan: {reg_val}% p.a., Direct Plan: {dir_val}% p.a.",
                    "source_id": c["source_id"],
                    "source_title": c["source_title"],
                    "source_url": c["source_url"],
                    "updated_at": c.get("published_at", ""),
                    "raw": text[:500],
                }
                break
        if scheme not in results:
            # Try factsheet
            for c in scheme_chunks(chunks, scheme, {"factsheet"}):
                text = c["text"]
                if "expense" in text.lower() or "ter" in text.lower():
                    pcts = re.findall(r"(\d+\.\d+)%", text)
                    if pcts:
                        results[scheme] = {
                            "value": f"Found percentages: {', '.join(p + '%' for p in pcts[:4])}",
                            "source_id": c["source_id"],
                            "source_title": c["source_title"],
                            "source_url": c["source_url"],
                            "updated_at": c.get("published_at", ""),
                            "raw": text[:500],
                        }
                        break
    return results


def extract_exit_load(chunks):
    results = {}
    for scheme in SCHEMES:
        for c in scheme_chunks(chunks, scheme, {"kim", "sid"}):
            text = c["text"]
            if "exit load" in text.lower() and ("redeemed" in text.lower() or "nil" in text.lower() or "%" in text):
                results[scheme] = {
                    "source_id": c["source_id"],
                    "source_title": c["source_title"],
                    "source_url": c["source_url"],
                    "updated_at": c.get("published_at", ""),
                    "raw": text[:600],
                }
                break
    return results


def extract_benchmark(chunks):
    results = {}
    for scheme in SCHEMES:
        for c in scheme_chunks(chunks, scheme, {"kim", "factsheet"}):
            text = c["text"]
            if "benchmark" in text.lower():
                results[scheme] = {
                    "source_id": c["source_id"],
                    "source_title": c["source_title"],
                    "source_url": c["source_url"],
                    "updated_at": c.get("published_at", ""),
                    "raw": text[:500],
                }
                break
    return results


def extract_riskometer(chunks):
    results = {}
    for scheme in SCHEMES:
        for c in scheme_chunks(chunks, scheme, {"kim", "factsheet"}):
            text = c["text"]
            if "riskometer" in text.lower() or "risk level" in text.lower():
                results[scheme] = {
                    "source_id": c["source_id"],
                    "source_title": c["source_title"],
                    "source_url": c["source_url"],
                    "updated_at": c.get("published_at", ""),
                    "raw": text[:500],
                }
                break
    return results


def extract_min_sip(chunks):
    results = {}
    for scheme in SCHEMES:
        for c in scheme_chunks(chunks, scheme, {"kim", "sid"}):
            text = c["text"]
            if "sip" in text.lower() and ("rs" in text.lower() or "minimum" in text.lower()):
                if "installment" in text.lower() or "amount" in text.lower() or "daily" in text.lower():
                    results[scheme] = {
                        "source_id": c["source_id"],
                        "source_title": c["source_title"],
                        "source_url": c["source_url"],
                        "updated_at": c.get("published_at", ""),
                        "raw": text[:600],
                    }
                    break
    return results


def extract_lock_in(chunks):
    results = {}
    for scheme in SCHEMES:
        for c in scheme_chunks(chunks, scheme, {"kim", "sid"}):
            text = c["text"]
            if "lock" in text.lower() and ("3 year" in text.lower() or "three year" in text.lower() or "nil" in text.lower()):
                results[scheme] = {
                    "source_id": c["source_id"],
                    "source_title": c["source_title"],
                    "source_url": c["source_url"],
                    "updated_at": c.get("published_at", ""),
                    "raw": text[:500],
                }
                break
    return results


def extract_fund_manager(chunks):
    results = {}
    for scheme in SCHEMES:
        for c in scheme_chunks(chunks, scheme, {"factsheet", "kim"}):
            text = c["text"]
            if "fund manager" in text.lower():
                results[scheme] = {
                    "source_id": c["source_id"],
                    "source_title": c["source_title"],
                    "source_url": c["source_url"],
                    "updated_at": c.get("published_at", ""),
                    "raw": text[:500],
                }
                break
    return results


def extract_investment_objective(chunks):
    results = {}
    for scheme in SCHEMES:
        for c in scheme_chunks(chunks, scheme, {"kim", "sid"}):
            text = c["text"]
            if "investment objective" in text.lower() or "scheme objective" in text.lower():
                results[scheme] = {
                    "source_id": c["source_id"],
                    "source_title": c["source_title"],
                    "source_url": c["source_url"],
                    "updated_at": c.get("published_at", ""),
                    "raw": text[:600],
                }
                break
    return results


def extract_min_lumpsum(chunks):
    results = {}
    for scheme in SCHEMES:
        for c in scheme_chunks(chunks, scheme, {"kim", "sid"}):
            text = c["text"]
            tl = text.lower()
            if ("minimum" in tl and ("purchase" in tl or "application" in tl or "investment" in tl)) and ("rs" in tl or "500" in tl or "1000" in tl or "5000" in tl):
                results[scheme] = {
                    "source_id": c["source_id"],
                    "source_title": c["source_title"],
                    "source_url": c["source_url"],
                    "updated_at": c.get("published_at", ""),
                    "raw": text[:600],
                }
                break
    return results


def extract_plans_options(chunks):
    results = {}
    for scheme in SCHEMES:
        for c in scheme_chunks(chunks, scheme, {"kim", "sid"}):
            text = c["text"]
            tl = text.lower()
            if ("growth" in tl or "idcw" in tl) and ("regular" in tl or "direct" in tl):
                results[scheme] = {
                    "source_id": c["source_id"],
                    "source_title": c["source_title"],
                    "source_url": c["source_url"],
                    "updated_at": c.get("published_at", ""),
                    "raw": text[:500],
                }
                break
    return results


def extract_statement_guidance(chunks):
    results = []
    for c in chunks:
        text = c["text"].lower()
        if "account statement" in text or "consolidated account" in text:
            if "5 business days" in text or "cas" in text or "capital gain" in text:
                results.append({
                    "source_id": c["source_id"],
                    "source_title": c["source_title"],
                    "source_url": c["source_url"],
                    "updated_at": c.get("published_at", ""),
                    "raw": c["text"][:500],
                })
    return results


if __name__ == "__main__":
    chunks = load_chunks()
    print(f"Loaded {len(chunks)} chunks\n")

    extractors = {
        "expense_ratio": extract_ter,
        "exit_load": extract_exit_load,
        "benchmark": extract_benchmark,
        "riskometer": extract_riskometer,
        "min_sip": extract_min_sip,
        "lock_in": extract_lock_in,
        "fund_manager": extract_fund_manager,
        "investment_objective": extract_investment_objective,
        "min_lumpsum": extract_min_lumpsum,
        "plans_options": extract_plans_options,
    }

    for fact_type, extractor in extractors.items():
        print(f"\n{'='*60}")
        print(f"FACT TYPE: {fact_type}")
        print(f"{'='*60}")
        results = extractor(chunks)
        for scheme in SCHEMES:
            if scheme in results:
                r = results[scheme]
                print(f"\n  {scheme}:")
                print(f"  Source: {r['source_id']}")
                if "value" in r:
                    print(f"  Value: {r['value']}")
                print(f"  Raw: {r['raw'][:400]}")
            else:
                print(f"\n  {scheme}: NOT FOUND")

    print(f"\n{'='*60}")
    print("STATEMENT GUIDANCE (general)")
    print(f"{'='*60}")
    stmts = extract_statement_guidance(chunks)
    for s in stmts[:5]:
        print(f"\n  Source: {s['source_id']}")
        print(f"  Raw: {s['raw'][:400]}")
