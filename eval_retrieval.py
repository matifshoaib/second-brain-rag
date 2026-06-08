#!/usr/bin/env python3
"""
eval_retrieval.py — systematic retrieval-quality proof across all 15 vaults.

Runs a fixed test set of natural-language queries. For each, it checks whether
the EXPECTED source note appears in the retrieved hits, and at what rank.
Produces a pass/fail matrix per vault and an overall accuracy score.

A query PASSES if its expected note path appears in the top-K retrieved hits
(scored hits, before graph-hop). "Top-1" and "Top-K" are both reported so you
can show both strict and lenient accuracy.

This is the proof artifact: run it AFTER the prefix fix + re-embed.

Usage:
  python3 eval_retrieval.py                 # console report
  python3 eval_retrieval.py --md report.md  # also write a Markdown report
"""
import sys
import argparse

from retrieval import retrieve

# ---------------------------------------------------------------------------
# TEST SET — each query maps to a substring of the REAL note path that should
# surface. Substring match keeps it robust to the vault-prefix path form.
# One+ query per vault, phrased as a natural question (the failure mode we fixed).
# ---------------------------------------------------------------------------
TESTS = [
    # vault, natural-language query, expected note-path substring
    ("Card-Payments-Vault",
     "How does card payment reconciliation work end to end?",
     "Reconciliation-Pipeline"),
    ("Card-Payments-Vault",
     "What is the difference between the issuer host and the acquirer host?",
     "Issuer-Acquirer-Hosts"),

    ("SWIFT-Vault",
     "How does Canada's high value payment system LYNX work?",
     "LYNX-Canada-HVPS"),
    ("SWIFT-Vault",
     "What sanctions screening happens on a SWIFT payment?",
     "Compliance-Screening-SWIFT"),

    ("Open-Banking-RTR-Vault",
     "Who is liable for APP fraud in open banking?",
     "Fraud-Including-APP-Fraud"),
    ("Open-Banking-RTR-Vault",
     "What is Canada's consumer-driven banking framework?",
     "Canadian-Consumer-Driven-Banking-Framework"),

    ("AAIR-Vault",
     "What does the EU AI Act require for high-risk AI systems?",
     "EU-AI-Act"),
    ("AAIR-Vault",
     "Explain the NIST AI RMF map function",
     "NIST-AI-RMF-Map-Function"),

    ("Treasury_Vault",
     "How is foreign exchange risk managed in treasury?",
     "FX-Risk-Management"),

    ("GenAI-for-Banking",
     "What are the OWASP top 10 risks for large language models?",
     "OWASP-LLM-Top-10"),
    ("GenAI-for-Banking",
     "How do I design a retrieval augmented generation architecture for banking?",
     "Banking-RAG-Reference-Architecture"),

    ("Modern-Data-Architecture-Vault",
     "What is the difference between a data fabric and a data mesh?",
     "Data-Fabric-vs-Data-Mesh"),

    ("Service-Mesh-Vault",
     "How does mutual TLS provide zero trust in a service mesh?",
     "mTLS-and-Zero-Trust"),

    ("AWS-Well-Architected",
     "What does the AWS security pillar say about data protection?",
     "SEC-Data-Protection"),

    ("Azure Architect Vault",
     "Should I use Azure Virtual WAN or a hub and spoke network?",
     "Virtual WAN vs Hub-Spoke"),

    ("CRISC Knowledge Vault",
     "How do I set a key risk indicator threshold?",
     "KRI Threshold Setting"),

    ("CBAP Knowledge Vault",
     "How do I write a BRD that survives regulatory scrutiny?",
     "Writing a BRD That Survives Regulatory Scrutiny"),

    ("PMP Knowledge Vault",
     "What are the common patterns in financial IT project failures?",
     "Pattern of Financial IT Failures"),

    ("ISO27001 Knowledge Vault",
     "How does ISO 27001 map to OSFI B-13?",
     "OSFI B-13 × ISO 27001 Alignment"),

    ("The-Architects-Codex",
     "What is the difference between TLS SSL and mTLS?",
     "TLS-and-mTLS-Deep-Dive"),
    ("The-Architects-Codex",
     "How do I migrate cryptography to be quantum safe?",
     "PQC-Migration-and-Crypto-Agility"),
]


def run():
    rows = []
    for vault, query, expect in TESTS:
        out = retrieve(query)
        # scored hits only (exclude graph-hop context, which has similarity None)
        scored = [h for h in out["hits"] if h.get("similarity") is not None]
        paths = [h["metadata"].get("note_path", "") for h in scored]

        rank = None
        for i, p in enumerate(paths, 1):
            if expect in p:
                rank = i
                break

        top_sim = scored[0]["similarity"] if scored else 0.0
        rows.append({
            "vault": vault,
            "query": query,
            "expect": expect,
            "rank": rank,
            "refused": out["refused"],
            "top_sim": top_sim,
            "top_hit": paths[0] if paths else "(none)",
        })
    return rows


def report(rows, md_path=None):
    n = len(rows)
    top1 = sum(1 for r in rows if r["rank"] == 1)
    topk = sum(1 for r in rows if r["rank"] is not None)

    def line(r):
        if r["rank"] == 1:
            verdict = "PASS (rank 1)"
        elif r["rank"] is not None:
            verdict = f"PASS (rank {r['rank']})"
        elif r["refused"]:
            verdict = "FAIL (refused)"
        else:
            verdict = "FAIL (wrong notes)"
        return verdict

    print("\n" + "=" * 78)
    print("RETRIEVAL EVALUATION — Second Brain RAG")
    print("=" * 78)
    for r in rows:
        v = line(r)
        flag = "✓" if r["rank"] is not None else "✗"
        print(f"{flag} [{v:<18}] {r['vault']}")
        print(f"    Q: {r['query']}")
        print(f"    expect: …{r['expect']}   top_sim={r['top_sim']:.3f}")
        if r["rank"] is None:
            print(f"    got instead: {r['top_hit']}")
    print("=" * 78)
    print(f"Top-1 accuracy (correct note ranked #1): {top1}/{n} = {100*top1/n:.0f}%")
    print(f"Top-K accuracy (correct note in top {len(rows) and 'K'}): {topk}/{n} = {100*topk/n:.0f}%")
    print("=" * 78)

    if md_path:
        with open(md_path, "w") as f:
            f.write("# Retrieval Evaluation — Second Brain RAG\n\n")
            f.write(f"**Test queries:** {n} across 15 vaults  \n")
            f.write(f"**Top-1 accuracy:** {top1}/{n} ({100*top1/n:.0f}%)  \n")
            f.write(f"**Top-K accuracy:** {topk}/{n} ({100*topk/n:.0f}%)\n\n")
            f.write("| Vault | Query | Expected note | Result | Top sim |\n")
            f.write("|---|---|---|---|---|\n")
            for r in rows:
                f.write(f"| {r['vault']} | {r['query']} | …{r['expect']} | "
                        f"{line(r)} | {r['top_sim']:.3f} |\n")
        print(f"\nMarkdown report written to: {md_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", help="also write a Markdown report to this path")
    args = ap.parse_args()
    report(run(), md_path=args.md)
