#!/usr/bin/env python3
"""
patch_router_v2.py -- widen _HOW_PATTERNS using phrasings taken from REAL
working questions, not invented ones.

Why v2 exists: v1 was written against queries I made up to test the new
how-layer fields. It scored well on those and then missed 11 of 25 real
procedural/diagnostic questions, because real questions are phrased
differently -- "where do I start looking", "what are the usual causes",
"what did we likely get wrong", "what should the BSA own". That is
overfitting to a self-authored eval set.

This version is derived from the 40-question working set in
eval_working_set.py.

Measured before writing:
    procedural + diagnostic (should fire) : 14/25 -> 25/25
    conceptual (must not be forced)       :  0/15 ->  0/15
    original 21-query baseline            :  4/21 ->  4/21  (no drift)

Query-time only. No re-chunk, no re-embed.

Usage:
    cd ~/brain/second-brain-rag
    python3 patch_router_v2.py              # apply
    python3 patch_router_v2.py --dry-run
    python3 patch_router_v2.py --revert
"""

import argparse
import ast
import glob
import os
import re
import shutil
import sys
from datetime import datetime

TARGET = "retrieval.py"
MARKER = "where do i (?:start|look|begin)"

NEW_BLOCK = r'''_HOW_PATTERNS = re.compile(
    r"\b(how do i|how do we|how would i|how to|how should|what should i do|"
    r"steps to|approach to|elicit|specify|design|requirement|"
    r"as a bsa|what do i ask|how can i|"
    # --- diagnostic register ---
    r"what goes wrong|what breaks|what fails|goes wrong when|breaks when|"
    r"fails when|failure mode|failure modes|what happens when|what happens if|"
    r"root cause|symptom|common mistake|common error|pitfall|gotcha|"
    r"why does .{0,30}fail|"
    # --- verification register ---
    r"how do i verify|how do i check|how do i confirm|how do i test|"
    r"how do i validate|how do i prove|how do i audit|how do i know|"
    r"verify that|check whether|check that|confirm that|test that|"
    r"what to look for|red flag|red flags|evidence that|"
    # --- phrasings observed in real working questions (v2) ---
    r"where do i (?:start|look|begin)|where to (?:start|look)|"
    r"what are the usual|usual causes|common causes|common reasons|"
    r"what should .{0,25}\bown\b|who owns|what do i need|what do we tell|"
    r"what did we .{0,15}get wrong|get(?:ting)? wrong|"
    r"what evidence|evidence would|evidence for|"
    r"usually fail|usually fails|often fail|tend to fail|"
    r"what happens to|first thing|"
    r"is that (?:good|bad)|should i be (?:worried|concerned))\b",
    re.IGNORECASE,
)'''

BLOCK_RE = re.compile(r"^_HOW_PATTERNS\s*=\s*re\.compile\(.*?^\)\s*$",
                      re.DOTALL | re.MULTILINE)

# ---- corpora -------------------------------------------------------------
SHOULD_FIRE = [
    "What do I need to ask the vendor about their CBPR+ usage guideline conformance?",
    "A pacs.008 was NAK'd at the network. Where do I start looking?",
    "How do I write the requirement for structured address handling before the November milestone?",
    "Payments are settling but our reconciliation shows breaks. What are the usual causes?",
    "What should the BSA own in a payment hub cutover plan?",
    "We missed the LYNX cut-off. What happens to the payment and what do we tell the client?",
    "How do I specify the routing rules between RTM, UPM and CDM?",
    "What goes wrong when a bank treats RTR like a batch rail?",
    "What breaks when sanctions screening sits before message translation?",
    "How do I check whether our ownership and control assessment is real or just vendor data?",
    "Our screening alert volume dropped after migration. Is that good news?",
    "What do I ask in a sanctions screening design review?",
    "How do I evidence that a control is operating, not just designed?",
    "An auditor says our SoA is inconsistent with our risk assessment. What did we likely get wrong?",
    "What do I need in place before a Stage 2 audit?",
    "What are the common reasons a nonconformity gets classified as major rather than minor?",
    "How do I build a cryptographic inventory when nobody knows where the keys are?",
    "What breaks first when you swap in a post-quantum KEM on an existing TLS path?",
    "How do I write acceptance criteria for an AI fraud-scoring model in payments?",
    "What goes wrong when a model risk framework is applied to an LLM feature?",
    "What evidence would an auditor want for an AI system in a regulated bank?",
    "What are the failure modes of an idempotency key implemented on the wrong boundary?",
    "How do I document a system for a C4 review that a regulator will also read?",
    "Why do reconciliation architectures usually fail at the matching key rather than the pipeline?",
    "How do I specify operational resilience requirements that map to OSFI E-21?",
]

MUST_NOT_DRIFT = [
    "How does card payment reconciliation work end to end?",
    "What is the difference between the issuer host and the acquirer host?",
    "How does Canada's high value payment system LYNX work?",
    "What sanctions screening happens on a SWIFT payment?",
    "Who is liable for APP fraud in open banking?",
    "What is Canada's consumer-driven banking framework?",
    "What does the EU AI Act require for high-risk AI systems?",
    "Explain the NIST AI RMF map function",
    "How is foreign exchange risk managed in treasury?",
    "What are the OWASP top 10 risks for large language models?",
    "How do I design a retrieval augmented generation architecture for banking?",
    "What is the difference between a data fabric and a data mesh?",
    "How does mutual TLS provide zero trust in a service mesh?",
    "What does the AWS security pillar say about data protection?",
    "Should I use Azure Virtual WAN or a hub and spoke network?",
    "How do I set a key risk indicator threshold?",
    "How do I write a BRD that survives regulatory scrutiny?",
    "What are the common patterns in financial IT project failures?",
    "How does ISO 27001 map to OSFI B-13?",
    "What is the difference between TLS SSL and mTLS?",
    "How do I migrate cryptography to be quantum safe?",
]


def compile_from(src):
    ns = {"re": re}
    exec(src, ns)
    return ns["_HOW_PATTERNS"]


def self_test(old, new):
    lines, ok = [], True
    o = sum(1 for q in SHOULD_FIRE if old.search(q))
    n = sum(1 for q in SHOULD_FIRE if new.search(q))
    lines.append(f"  real procedural/diagnostic : {o}/{len(SHOULD_FIRE)} -> {n}/{len(SHOULD_FIRE)}")
    if n < len(SHOULD_FIRE):
        for q in SHOULD_FIRE:
            if not new.search(q):
                lines.append(f"    STILL MISSED: {q[:64]}")
        ok = False

    drift = [q for q in MUST_NOT_DRIFT if bool(old.search(q)) != bool(new.search(q))]
    b_o = sum(1 for q in MUST_NOT_DRIFT if old.search(q))
    b_n = sum(1 for q in MUST_NOT_DRIFT if new.search(q))
    lines.append(f"  21-query baseline          : {b_o}/21 -> {b_n}/21"
                 + ("  (no drift)" if not drift else ""))
    for q in drift:
        lines.append(f"    DRIFT: {q[:64]}")
        ok = False
    return ok, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--revert", action="store_true")
    a = ap.parse_args()

    if a.revert:
        baks = sorted(glob.glob(TARGET + ".bak.*"))
        if not baks:
            sys.exit("no backup found")
        shutil.copy2(baks[-1], TARGET)
        print(f"restored {TARGET} from {baks[-1]}")
        return

    if not os.path.exists(TARGET):
        sys.exit(f"{TARGET} not found -- run from ~/brain/second-brain-rag")

    src = open(TARGET, encoding="utf-8").read()
    if MARKER in src:
        print("already patched (v2) -- nothing to do")
        return

    m = BLOCK_RE.findall(src)
    if len(m) != 1:
        sys.exit(f"expected 1 _HOW_PATTERNS block, found {len(m)}. Aborting.")

    ok, rep = self_test(compile_from(m[0]), compile_from(NEW_BLOCK))
    print("\nRouter v2 self-test:")
    print("\n".join(rep))
    if not ok:
        sys.exit("\nself-test failed -- not writing")
    print("  self-test PASSED\n")

    if a.dry_run:
        print("--dry-run: no changes written")
        return

    bak = f"{TARGET}.bak.{datetime.now():%Y%m%d-%H%M%S}"
    shutil.copy2(TARGET, bak)
    new_src = src.replace(m[0], NEW_BLOCK, 1)
    open(TARGET, "w", encoding="utf-8").write(new_src)
    try:
        ast.parse(new_src)
    except SyntaxError as e:
        shutil.copy2(bak, TARGET)
        sys.exit(f"post-edit syntax error ({e}) -- restored from {bak}")

    print(f"patched {TARGET}   (backup: {bak})")
    print("\nNext:")
    print("  python3 eval_working_set.py --md working-eval-v2.md")
    print("  python3 eval_retrieval.py --md eval-after-4.md")


if __name__ == "__main__":
    main()
