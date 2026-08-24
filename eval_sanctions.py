#!/usr/bin/env python3
"""
eval_sanctions.py -- pilot evaluation for the six-field how-layer.

Does NOT modify eval_retrieval.py. Reuses its run() and report() with a
different test set.

Two groups of queries:

  A. NEW-FIELD PROBES -- phrased so the answer lives in bsa_failure or
     bsa_verify. These cannot pass on a four-field vault, because the content
     does not exist there. They test that the new fields are retrievable at
     all, and at what rank.

  B. REGRESSION CONTROLS -- answerable from the note BODY, which is unchanged.
     These are the ones that matter. If adding two fields pushes body content
     down or steals rank, it shows up here. A pass on group A with a
     regression in group B means the schema change is a net loss.

Usage:
  python3 eval_sanctions.py                    # both groups
  python3 eval_sanctions.py --group A          # new-field probes only
  python3 eval_sanctions.py --group B          # regression controls only
  python3 eval_sanctions.py --md sanctions-eval.md
"""
import argparse
import eval_retrieval as E

# (group, vault, query, expected note-path substring)
SANCTIONS_TESTS_FULL = [

    # ---- GROUP A: answerable only from bsa_failure / bsa_verify ----
    ("A", "The-Architects-Codex",
     "What breaks when sanctions screening runs before message translation?",
     "Sanctions-Screening-in-ISO-20022-Payment-Flows"),

    ("A", "The-Architects-Codex",
     "How do I check whether our ownership and control assessment is real or just vendor data?",
     "Canada-Sanctions-Framework-SEMA-JVCFOA-UN-Act"),

    ("A", "The-Architects-Codex",
     "What goes wrong when SDN and SSI entries are loaded into a single list?",
     "OFAC-Sanctions-Programs-and-the-50-Percent-Rule"),

    ("A", "The-Architects-Codex",
     "How can I verify that every screening system is using the same list version?",
     "Sanctions-Screening-Controls-and-Tuning"),

    ("A", "The-Architects-Codex",
     "What is the failure where one corridor is fixed but the root cause stays live elsewhere?",
     "Sanctions-Program-Governance-and-Enforcement"),

    ("A", "The-Architects-Codex",
     "How do I test that a general licence suppression rule stops when the licence expires?",
     "OFAC-Sanctions-Programs-and-the-50-Percent-Rule"),

    # ---- GROUP B: regression controls, answerable from note bodies ----
    ("B", "The-Architects-Codex",
     "Does the OFAC 50 percent rule aggregate ownership across blocked persons?",
     "OFAC-Sanctions-Programs-and-the-50-Percent-Rule"),

    ("B", "The-Architects-Codex",
     "What is the deemed ownership rule under SEMA and the JVCFOA?",
     "Canada-Sanctions-Framework-SEMA-JVCFOA-UN-Act"),

    ("B", "The-Architects-Codex",
     "How does AIS manipulation work in maritime sanctions evasion?",
     "Sanctions-Evasion-Typologies"),

    ("B", "The-Architects-Codex",
     "What is the UK reporting deadline for informing OFSI of a designated person?",
     "EU-and-UK-Sanctions-Frameworks"),

    ("B", "The-Architects-Codex",
     "What is the difference between blocking and rejecting a payment?",
     "OFAC-Sanctions-Programs-and-the-50-Percent-Rule"),

    ("B", "The-Architects-Codex",
     "Why does ISO 20022 structured party data improve sanctions screening precision?",
     "Sanctions-Screening-in-ISO-20022-Payment-Flows"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", choices=["A", "B"], help="restrict to one group")
    ap.add_argument("--md", help="also write a Markdown report")
    a = ap.parse_args()

    tests = [t for t in SANCTIONS_TESTS_FULL
             if a.group is None or t[0] == a.group]

    label = {"A": "NEW-FIELD PROBES", "B": "REGRESSION CONTROLS"}
    if a.group:
        print(f"\n>>> Group {a.group}: {label[a.group]}  ({len(tests)} queries)")
    else:
        na = sum(1 for t in SANCTIONS_TESTS_FULL if t[0] == "A")
        nb = sum(1 for t in SANCTIONS_TESTS_FULL if t[0] == "B")
        print(f"\n>>> Group A (new-field probes): {na}   "
              f"Group B (regression controls): {nb}")

    # eval_retrieval.run() reads the module-global TESTS as (vault, query, expect)
    E.TESTS = [(v, q, x) for _g, v, q, x in tests]
    rows = E.run()

    for r, t in zip(rows, tests):
        r["vault"] = f"[{t[0]}] {r['vault']}"

    E.report(rows, md_path=a.md)

    # per-group summary when running both
    if a.group is None:
        for g in ("A", "B"):
            sub = [r for r in rows if r["vault"].startswith(f"[{g}]")]
            if not sub:
                continue
            t1 = sum(1 for r in sub if r["rank"] == 1)
            tk = sum(1 for r in sub if r["rank"] is not None)
            print(f"Group {g} ({label[g]}): Top-1 {t1}/{len(sub)}  "
                  f"Top-K {tk}/{len(sub)}")
        print("Group B is the one that decides. A regression there outweighs "
              "any gain in A.\n")


if __name__ == "__main__":
    main()
