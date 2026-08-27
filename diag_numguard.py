#!/usr/bin/env python3
"""Why did numguard report nothing? Read-only."""
import re, generate
from retrieval import retrieve

Q = ("We are introducing AI-driven fraud scoring into RTR payments. "
     "What operational, regulatory, resilience, and governance concerns emerge?")

r = retrieve(Q)
context  = generate._build_context(r["hits"])
practice = generate._how_layer_context(Q)
retrieved = context + "\n" + practice

print(f"context chars : {len(context)}")
print(f"practice chars: {len(practice)}")
digits = set(re.findall(r"\d+(?:\.\d+)?", retrieved.replace(",", "")))
for probe in ("800", "50", "100", "200", "60", "10"):
    print(f"  '{probe}' in retrieved corpus: {probe in digits}")

print("\n-- notes actually retrieved --")
for p in dict.fromkeys(h["metadata"].get("note_path","") for h in r["hits"]):
    print("   ", p)

out = generate.answer(Q)
s = out["structured"]
syn = s.get("synthesis", "")
print(f"\nsynthesis chars: {len(syn)}")
print("synthesis mentions 800:", "800" in syn)
print("unverified_values:", s.get("unverified_values"))
print("confidence:", s.get("confidence"), "|", s.get("confidence_reason"))

hits = [m.group(0) for m in generate._NUM_CLAIM.finditer(syn)][:15]
print("\nraw numeric matches in synthesis:", hits)
