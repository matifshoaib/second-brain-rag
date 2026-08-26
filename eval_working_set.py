#!/usr/bin/env python3
"""
eval_working_set.py -- run real working questions against the vault and
produce a report you rate by hand.

This is deliberately NOT eval_retrieval.py. That harness asks "did the note I
already know is correct come back first?" -- it measures retrieval mechanics
against a known answer key.

This one asks a different question: "if I typed what I would actually type at
work, is the answer any good?" There is no answer key, because writing one
would mean picking notes I already know exist, which grades the vault against
itself.

Instead it captures, per question:
  - the synthesized answer
  - which notes were retrieved, and their similarity
  - whether how_layer chunks surfaced at all
  - whether each practitioner card ECHOES the question or ADDS to it
    (cosine between the query and the card -- high similarity means the card
    handed the question back)

You rate two columns by hand: ANSWER (1-5) and CARDS (add / echo / absent).
The output is a repair queue ordered by what actually failed.

Usage:
    python3 eval_working_set.py                       # all questions
    python3 eval_working_set.py --category payments   # one category
    python3 eval_working_set.py --limit 10            # first N
    python3 eval_working_set.py --md working-eval.md  # write report
    python3 eval_working_set.py --list                # just print questions
"""

import argparse
import re
import sys
import textwrap
from datetime import datetime

# ---------------------------------------------------------------------------
# 40 working questions.
#
# These are phrased the way the question arrives in real work -- mid-thread,
# assuming context, often diagnostic. They are drawn from the DOMAIN, not from
# the vault's table of contents, so a miss is information rather than an error.
#
# Mix by design:
#   ~1/3  conceptual   ("what is / how does")        -> should hit note bodies
#   ~1/3  procedural   ("how do I / what do I ask")  -> should hit the how-layer
#   ~1/3  diagnostic   ("what breaks / why did")     -> the register the vault
#                                                       is thinnest on
# ---------------------------------------------------------------------------

QUESTIONS = [

    # ---------------- payments: ISO 20022 and SWIFT ----------------
    ("payments", "conceptual",
     "What actually breaks if we truncate a party name during MX to MT translation?"),
    ("payments", "procedural",
     "What do I need to ask the vendor about their CBPR+ usage guideline conformance?"),
    ("payments", "diagnostic",
     "A pacs.008 was NAK'd at the network. Where do I start looking?"),
    ("payments", "conceptual",
     "How is a UETR generated and preserved across a cover payment pair?"),
    ("payments", "procedural",
     "How do I write the requirement for structured address handling before the November milestone?"),
    ("payments", "diagnostic",
     "Payments are settling but our reconciliation shows breaks. What are the usual causes?"),
    ("payments", "conceptual",
     "What is the difference between ACSP and ACSC in a pacs.002 and why does it matter?"),
    ("payments", "procedural",
     "What should the BSA own in a payment hub cutover plan?"),

    # ---------------- payments: Canadian rails ----------------
    ("canada-rails", "conceptual",
     "How does intraday liquidity get managed against LYNX settlement?"),
    ("canada-rails", "diagnostic",
     "We missed the LYNX cut-off. What happens to the payment and what do we tell the client?"),
    ("canada-rails", "procedural",
     "How do I specify the routing rules between RTM, UPM and CDM?"),
    ("canada-rails", "conceptual",
     "What is RTR and how does it differ from LYNX in liability terms?"),
    ("canada-rails", "diagnostic",
     "What goes wrong when a bank treats RTR like a batch rail?"),

    # ---------------- financial crime ----------------
    ("fincrime", "conceptual",
     "What is the difference between blocking and rejecting a payment?"),
    ("fincrime", "diagnostic",
     "What breaks when sanctions screening sits before message translation?"),
    ("fincrime", "procedural",
     "How do I check whether our ownership and control assessment is real or just vendor data?"),
    ("fincrime", "conceptual",
     "Does the OFAC 50 percent rule aggregate across different sanctions programs?"),
    ("fincrime", "diagnostic",
     "Our screening alert volume dropped after migration. Is that good news?"),
    ("fincrime", "procedural",
     "What do I ask in a sanctions screening design review?"),

    # ---------------- security standards and audit ----------------
    ("security", "conceptual",
     "How does ISO 27001 Annex A map onto a payment screening system?"),
    ("security", "procedural",
     "How do I evidence that a control is operating, not just designed?"),
    ("security", "diagnostic",
     "An auditor says our SoA is inconsistent with our risk assessment. What did we likely get wrong?"),
    ("security", "conceptual",
     "What changed between ISO 27001:2013 and 2022 that actually affects an audit?"),
    ("security", "procedural",
     "What do I need in place before a Stage 2 audit?"),
    ("security", "diagnostic",
     "What are the common reasons a nonconformity gets classified as major rather than minor?"),

    # ---------------- cryptography and PQC ----------------
    ("crypto", "conceptual",
     "Why does harvest-now-decrypt-later change the timeline for a payments estate?"),
    ("crypto", "procedural",
     "How do I build a cryptographic inventory when nobody knows where the keys are?"),
    ("crypto", "diagnostic",
     "What breaks first when you swap in a post-quantum KEM on an existing TLS path?"),
    ("crypto", "conceptual",
     "What is crypto-agility in practice, beyond the slogan?"),

    # ---------------- AI governance and assurance ----------------
    ("ai-governance", "conceptual",
     "What does the EU AI Act actually require for a high-risk system?"),
    ("ai-governance", "procedural",
     "How do I write acceptance criteria for an AI fraud-scoring model in payments?"),
    ("ai-governance", "diagnostic",
     "What goes wrong when a model risk framework is applied to an LLM feature?"),
    ("ai-governance", "conceptual",
     "How does NIST AI RMF Govern differ from Manage in practice?"),
    ("ai-governance", "procedural",
     "What evidence would an auditor want for an AI system in a regulated bank?"),

    # ---------------- architecture and platform ----------------
    ("architecture", "conceptual",
     "When is event-driven the wrong choice for a payment flow?"),
    ("architecture", "diagnostic",
     "What are the failure modes of an idempotency key implemented on the wrong boundary?"),
    ("architecture", "procedural",
     "How do I document a system for a C4 review that a regulator will also read?"),
    ("architecture", "conceptual",
     "What does mTLS actually buy you inside a service mesh that TLS does not?"),
    ("architecture", "diagnostic",
     "Why do reconciliation architectures usually fail at the matching key rather than the pipeline?"),
    ("architecture", "procedural",
     "How do I specify operational resilience requirements that map to OSFI E-21?"),
]


def _cos(a, b):
    import math
    num = sum(x * y for x, y in zip(a, b))
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(y * y for y in b))
    return num / (da * db) if da and db else 0.0


def run(questions, embed_fn=None):
    from retrieval import retrieve
    rows = []
    for i, (cat, kind, q) in enumerate(questions, 1):
        print(f"  [{i}/{len(questions)}] {q[:64]}...", file=sys.stderr)
        try:
            out = retrieve(q)
        except Exception as e:
            rows.append({"cat": cat, "kind": kind, "q": q, "error": str(e)})
            continue

        scored = [h for h in out["hits"] if h.get("similarity") is not None]
        how = [h for h in scored
               if h["metadata"].get("chunk_type") == "how_layer"]

        # card echo: how similar is the how_layer text to the question itself?
        echo = None
        if how and embed_fn:
            try:
                qe = embed_fn(q)
                ce = embed_fn(how[0]["text"][:1500])
                echo = round(_cos(qe, ce), 3)
            except Exception:
                echo = None

        rows.append({
            "cat": cat, "kind": kind, "q": q,
            "how_mode": out.get("how_mode"),
            "refused": out.get("refused"),
            "top_sim": round(out.get("top_similarity", 0.0), 3),
            "n_scored": len(scored),
            "how_hit": bool(how),
            "how_rank": (scored.index(how[0]) + 1) if how else None,
            "echo": echo,
            "top_notes": [h["metadata"].get("note_path", "").split("/")[-1][:48]
                          for h in scored[:3]],
            "error": None,
        })
    return rows


def report(rows, md_path=None):
    n = len(rows)
    ok = [r for r in rows if not r.get("error")]
    refused = sum(1 for r in ok if r.get("refused"))
    how_fired = sum(1 for r in ok if r.get("how_mode"))
    how_hit = sum(1 for r in ok if r.get("how_hit"))
    echoes = [r["echo"] for r in ok if r.get("echo") is not None]

    print("\n" + "=" * 78)
    print("WORKING-QUESTION EVALUATION")
    print("=" * 78)

    for r in rows:
        if r.get("error"):
            print(f"\n[{r['cat']}/{r['kind']}] {r['q']}")
            print(f"    ERROR: {r['error'][:100]}")
            continue
        flag = "REFUSED" if r["refused"] else f"sim={r['top_sim']:.3f}"
        howtag = (f"how_layer@{r['how_rank']}" if r["how_hit"]
                  else ("how_mode-no-hit" if r["how_mode"] else "-"))
        echotag = f" echo={r['echo']}" if r.get("echo") is not None else ""
        print(f"\n[{r['cat']}/{r['kind']}] {r['q']}")
        print(f"    {flag}  {howtag}{echotag}")
        for p in r["top_notes"]:
            print(f"      - {p}")
        print(f"    ANSWER _/5    CARDS  add / echo / absent")

    print("\n" + "=" * 78)
    print(f"Questions           {n}")
    print(f"Refused             {refused}  ({refused/max(n,1):.0%})")
    print(f"how_mode fired      {how_fired}")
    print(f"how_layer retrieved {how_hit}")
    if echoes:
        echoes.sort()
        print(f"Card echo (cos to question)  median {echoes[len(echoes)//2]:.3f}  "
              f"max {echoes[-1]:.3f}")
        print("  >0.80 means the card is handing the question back, not adding to it.")
    print("=" * 78)

    by_kind = {}
    for r in ok:
        by_kind.setdefault(r["kind"], []).append(r)
    print("\nBy question type:")
    for k, v in sorted(by_kind.items()):
        hh = sum(1 for r in v if r["how_hit"])
        rf = sum(1 for r in v if r["refused"])
        avg = sum(r["top_sim"] for r in v) / len(v)
        print(f"  {k:12s} n={len(v):2d}  avg_sim={avg:.3f}  "
              f"how_layer={hh:2d}  refused={rf}")
    print()

    if md_path:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Working-question evaluation\n\n")
            f.write(f"_Run {datetime.now():%Y-%m-%d %H:%M}_ · {n} questions\n\n")
            f.write("Rate each row by hand. **Answer**: 1-5. "
                    "**Cards**: `add` (told me something the prose did not), "
                    "`echo` (restated the question or the prose), "
                    "`absent` (no practitioner layer surfaced).\n\n")
            f.write("| # | Category | Type | Question | Top sim | how_layer | Echo | Answer | Cards | Note |\n")
            f.write("|---|---|---|---|---|---|---|---|---|---|\n")
            for i, r in enumerate(rows, 1):
                if r.get("error"):
                    f.write(f"| {i} | {r['cat']} | {r['kind']} | {r['q']} | ERROR | | | | | |\n")
                    continue
                hl = f"rank {r['how_rank']}" if r["how_hit"] else "-"
                f.write(f"| {i} | {r['cat']} | {r['kind']} | {r['q']} | "
                        f"{r['top_sim']:.3f} | {hl} | "
                        f"{r['echo'] if r.get('echo') is not None else ''} |  |  |  |\n")
            f.write("\n## What to do with this\n\n")
            f.write("- **Answer 1-2** -> the vault has a content gap. Write the note.\n")
            f.write("- **Cards `echo`** -> the practitioner layer restates instead of adding. "
                    "This is the same defect as the formulaic `design` fields: repair, do not extend.\n")
            f.write("- **Cards `absent` on a procedural question** -> routing or retrieval issue, "
                    "not a content issue.\n")
            f.write("- **Refused** -> either a real gap or the similarity gate is too tight. "
                    "Check which before changing the threshold.\n")
        print(f"Markdown report written to: {md_path}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category")
    ap.add_argument("--kind", choices=["conceptual", "procedural", "diagnostic"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--md")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    qs = QUESTIONS
    if a.category:
        qs = [q for q in qs if q[0] == a.category]
    if a.kind:
        qs = [q for q in qs if q[1] == a.kind]
    if a.limit:
        qs = qs[:a.limit]

    if a.list:
        for cat, kind, q in qs:
            print(f"[{cat}/{kind}] {q}")
        return

    if not qs:
        sys.exit("no questions matched that filter")

    # optional: reuse the pipeline's own embedder for the echo metric
    embed_fn = None
    try:
        import httpx
        from retrieval import _embed_query
        _client = httpx.Client()
        embed_fn = lambda t: _embed_query(t, _client)
    except Exception:
        print("[note] echo metric unavailable (could not import _embed_query)",
              file=sys.stderr)

    print(f"Running {len(qs)} working questions...", file=sys.stderr)
    report(run(qs, embed_fn), md_path=a.md)


if __name__ == "__main__":
    main()
