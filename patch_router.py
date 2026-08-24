#!/usr/bin/env python3
"""
patch_router.py -- widen _HOW_PATTERNS in retrieval.py to recognise
diagnostic ("what goes wrong when...") and verification ("how do I check
that...") phrasing, so how_layer chunks compete for the questions the
bsa_failure and bsa_verify fields actually answer.

Query-time only. No re-chunk, no re-embed.

Safe by construction:
  - backs up retrieval.py to retrieval.py.bak.<timestamp>
  - refuses unless it finds exactly one _HOW_PATTERNS block
  - refuses if the file no longer parses after the edit (and restores)
  - idempotent: detects an already-patched file and exits cleanly
  - self-tests the new regex against three query sets before writing

Usage:
    cd ~/brain/second-brain-rag
    python3 patch_router.py              # apply
    python3 patch_router.py --dry-run    # show what would change
    python3 patch_router.py --revert     # restore newest backup
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
MARKER = "what goes wrong"          # presence => already patched

NEW_BLOCK = '''_HOW_PATTERNS = re.compile(
    r"\\b(how do i|how do we|how would i|how to|how should|what should i do|"
    r"steps to|approach to|elicit|specify|design|requirement|"
    r"as a bsa|what do i ask|how can i|"
    # --- diagnostic / failure register (bsa_failure) ---
    r"what goes wrong|what breaks|what fails|goes wrong when|breaks when|"
    r"fails when|failure mode|failure modes|what happens when|what happens if|"
    r"root cause|symptom|common mistake|common error|pitfall|gotcha|"
    r"why does .{0,30}fail|"
    # --- verification register (bsa_verify) ---
    r"how do i verify|how do i check|how do i confirm|how do i test|"
    r"how do i validate|how do i prove|how do i audit|how do i know|"
    r"verify that|check whether|check that|confirm that|test that|"
    r"what to look for|red flag|red flags|evidence that)\\b",
    re.IGNORECASE,
)'''

BLOCK_RE = re.compile(
    r"^_HOW_PATTERNS\s*=\s*re\.compile\(.*?^\)\s*$",
    re.DOTALL | re.MULTILINE,
)

# --- self-test corpora -----------------------------------------------------
GROUP_A = [  # must ALL fire (answerable from bsa_failure / bsa_verify)
    "What breaks when sanctions screening runs before message translation?",
    "How do I check whether our ownership and control assessment is real or just vendor data?",
    "What goes wrong when SDN and SSI entries are loaded into a single list?",
    "How can I verify that every screening system is using the same list version?",
    "What is the failure where one corridor is fixed but the root cause stays live elsewhere?",
    "How do I test that a general licence suppression rule stops when the licence expires?",
]
GROUP_B = [  # must NOT change (answerable from note bodies)
    "Does the OFAC 50 percent rule aggregate ownership across blocked persons?",
    "What is the deemed ownership rule under SEMA and the JVCFOA?",
    "How does AIS manipulation work in maritime sanctions evasion?",
    "What is the UK reporting deadline for informing OFSI of a designated person?",
    "What is the difference between blocking and rejecting a payment?",
    "Why does ISO 20022 structured party data improve sanctions screening precision?",
]
ORIG_21 = [  # must NOT change (the standing baseline)
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


def compile_from(block_src):
    ns = {"re": re}
    exec(block_src, ns)
    return ns["_HOW_PATTERNS"]


def self_test(old_rx, new_rx):
    """Returns (ok, report_lines)."""
    lines, ok = [], True

    a_old = sum(1 for q in GROUP_A if old_rx.search(q))
    a_new = sum(1 for q in GROUP_A if new_rx.search(q))
    lines.append(f"  Group A (failure/verify) : {a_old}/6 -> {a_new}/6")
    if a_new < len(GROUP_A):
        lines.append("    FAIL: not every diagnostic query fires how_mode")
        ok = False

    for name, corpus in (("Group B (bodies)", GROUP_B), ("Original 21", ORIG_21)):
        drift = [q for q in corpus if bool(old_rx.search(q)) != bool(new_rx.search(q))]
        b_old = sum(1 for q in corpus if old_rx.search(q))
        b_new = sum(1 for q in corpus if new_rx.search(q))
        lines.append(f"  {name:24s} : {b_old}/{len(corpus)} -> {b_new}/{len(corpus)}"
                     + ("  (no drift)" if not drift else ""))
        for q in drift:
            lines.append(f"    DRIFT: {q[:66]}")
            ok = False
    return ok, lines


def revert():
    baks = sorted(glob.glob(TARGET + ".bak.*"))
    if not baks:
        sys.exit("no backup found")
    shutil.copy2(baks[-1], TARGET)
    print(f"restored {TARGET} from {baks[-1]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--revert", action="store_true")
    a = ap.parse_args()

    if a.revert:
        return revert()

    if not os.path.exists(TARGET):
        sys.exit(f"{TARGET} not found -- run this from ~/brain/second-brain-rag")

    src = open(TARGET, encoding="utf-8").read()

    if MARKER in src:
        print("already patched -- nothing to do")
        return

    matches = BLOCK_RE.findall(src)
    if len(matches) != 1:
        sys.exit(f"expected exactly 1 _HOW_PATTERNS block, found {len(matches)}. "
                 "Aborting rather than guessing.")

    old_block = matches[0]
    old_rx = compile_from(old_block)
    new_rx = compile_from(NEW_BLOCK)

    ok, report = self_test(old_rx, new_rx)
    print("\nRouter self-test:")
    print("\n".join(report))
    if not ok:
        sys.exit("\nself-test failed -- not writing")
    print("  self-test PASSED\n")

    if a.dry_run:
        print("--dry-run: no changes written")
        return

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = f"{TARGET}.bak.{stamp}"
    shutil.copy2(TARGET, bak)

    new_src = src.replace(old_block, NEW_BLOCK, 1)
    open(TARGET, "w", encoding="utf-8").write(new_src)

    try:
        ast.parse(new_src)
    except SyntaxError as e:
        shutil.copy2(bak, TARGET)
        sys.exit(f"post-edit syntax error ({e}) -- restored from {bak}")

    print(f"patched {TARGET}   (backup: {bak})")
    print("Query-time change only. No re-chunk, no re-embed needed.")
    print("\nNext:")
    print("  python3 eval_sanctions.py --md sanctions-eval-2.md")
    print("  python3 eval_retrieval.py --md eval-after-2.md")


if __name__ == "__main__":
    main()
