"""Quick search for factsheet TER/AUM data for our 4 schemes."""
import json

chunks = json.loads(open("data/index/chunks.json", encoding="utf-8").read())
TARGET = {
    "Groww Large Cap Fund",
    "Groww ELSS Tax Saver Fund",
    "Groww Banking and Financial Services Fund",
    "Groww Nifty 50 Index Fund",
}

print("=== FACTSHEET DATA (TER/FUND SIZE/FUND MANAGER) ===\n")
for c in chunks:
    if c["source_id"].startswith("groww-factsheet"):
        t = c["text"]
        tl = t.lower()
        if "total expense ratio" in tl or "fund size" in tl:
            for s in c.get("scheme_names", []):
                if s in TARGET:
                    print(f"--- {s} [{c['source_id']}] ---")
                    print(t[:700])
                    print()
                    break

print("\n\n=== KIM DATA (EXIT LOAD / SIP / BENCHMARK / RISKOMETER) ===\n")
for c in chunks:
    if c["document_type"] in ("kim",):
        t = c["text"]
        tl = t.lower()
        for s in c.get("scheme_names", []):
            if s in TARGET:
                if "exit load" in tl and ("%" in t or "nil" in tl):
                    print(f"--- EXIT LOAD: {s} [{c['source_id']}] ---")
                    print(t[:700])
                    print()
                elif "minimum" in tl and "sip" in tl and "rs" in tl:
                    print(f"--- MIN SIP: {s} [{c['source_id']}] ---")
                    print(t[:700])
                    print()
                elif "fund manager" in tl and ("anupam" in tl or "kaustubh" in tl or "shashi" in tl or "aakash" in tl or "nikhil" in tl or "managing" in tl):
                    print(f"--- FUND MANAGER: {s} [{c['source_id']}] ---")
                    print(t[:700])
                    print()
                elif "riskometer" in tl and ("very high" in tl or "high" in tl or "moderate" in tl):
                    print(f"--- RISKOMETER: {s} [{c['source_id']}] ---")
                    print(t[:700])
                    print()
                break

print("\n\n=== TER NOTICE DATA ===\n")
for c in chunks:
    if c["document_type"] == "ter_notice":
        print(f"--- {c['source_id']} ---")
        print(c["text"][:700])
        print()
