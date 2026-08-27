#!/usr/bin/env python3
"""
patch_grounding_v2.py -- stop invented values, and make confidence honest.

Applies cleanly ON TOP OF patch_two_lane.py. Two independent fixes:

1. THE GROUNDING RULE (prompt)
   The cards currently invent numbers. The last RTR answer produced an 800ms
   pipeline budget decomposed into 50/100/50/200ms stages, a named
   XGBoost-then-neural architecture, 5-second friction delays, a 300ms
   fail-safe threshold, 250ms-over-1%-over-5-minutes, and a 10:1
   false-positive ratio. None of it was in the retrieved notes. It was
   internally consistent, which makes it harder to catch, not easier.

   The rule confines numbers, vendors, algorithms, named roles and clause
   numbers to what appears in the retrieved text, and requires a
   [value not in notes] marker where the shape is known but the value is not.

   This does NOT reduce card content. It constrains what may appear inside an
   item, not how many items a card has. The two-lane retrieval supplies the
   content; grounding stops the model filling leftover space with invention.

2. DETERMINISTIC CONFIDENCE (code, not prompt)
   Today confidence is whatever the model claims -- _normalize_structured only
   checks the string is one of three values. So an answer can report "high"
   while its own gaps list admits the notes do not cover the question. Asking
   the model nicely does not fix a self-report; computing it does.

   _calibrate_confidence() derives the value from observable signals:
       - retrieval strength (top semantic similarity)
       - number of declared gaps
       - number of [not in notes] markers across the dimension items
   and caps the model's claim accordingly. The model can lower confidence,
   never inflate it past what the evidence supports.

   A "confidence_reason" field is added so the calibration is inspectable
   rather than mysterious. The UI ignores unknown keys, so nothing breaks.

Answer-time only. No re-stamp, no re-chunk, no re-embed.

Tuning (env-overridable):
    CONF_SIM_LOW=0.68    below this, confidence is forced to low
    CONF_SIM_MED=0.78    below this, confidence is capped at medium

Usage:
    cd ~/brain/second-brain-rag
    python3 patch_grounding_v2.py --dry-run
    python3 patch_grounding_v2.py
    python3 patch_grounding_v2.py --revert
"""

import argparse
import ast
import glob
import os
import shutil
import sys
from datetime import datetime

TARGET = "generate.py"
MARKER = "_calibrate_confidence"

# ---- anchor 1: content rules in SYSTEM_PROMPT ----
A1 = "- Regulatory anchors must be lifted from the notes (D-SIB Hook / bsa_dsib content)."

A1_NEW = '''- Regulatory anchors must be lifted from the notes (D-SIB Hook / bsa_dsib content).

GROUNDING RULE -- specificity must come from the CONTEXT, never from your own knowledge of how such systems are usually built. A fabricated number is worse than a vague one: it looks authoritative and gets carried into a design review as though the notes supported it.

The following may appear in a dimension item or in the synthesis ONLY IF present in the CONTEXT or the PRACTICE LIBRARY:
  - any number: latency, timeout, SLA, percentile, threshold, score band, ratio, percentage, duration, deadline, dollar amount
  - any named product, vendor, model architecture, algorithm or library
  - any named internal role, team or committee the notes do not name
  - any regulation, guideline number or clause the notes do not cite

Where the retrieved material does not supply the value, you have exactly two options:
  1. Write the item in its correct SHAPE with the value marked absent:
       "Establish fail-safe routing that bypasses to static rules when scoring latency exceeds the agreed threshold [threshold not in notes]"
       "The pipeline SHALL complete within the agreed pre-submission latency budget [value not in notes]"
  2. Omit the item and record the missing value under "gaps".

DO NOT substitute a plausible industry-typical figure. "800ms", "sub-second", "99.99%", "10:1", "24 hours" are exactly the values that sound right and are unsupported. A decomposed budget that adds up internally is still fabrication if the notes never gave the numbers.

Naming the ROLE to ask is grounded and encouraged. Naming the THRESHOLD they would give you is not. "Ask fraud operations what false-positive ratio the analyst queue can absorb" is correct; "SHALL hold at 10:1" is invention unless the notes say so.

This rule does not license thinner cards. Keep the item counts -- mark the values instead.'''

# ---- anchor 2: confidence handling in _normalize_structured ----
A2 = '''    conf = s(d.get("confidence", "")).lower()
    if conf not in {"high", "medium", "low"}:
        conf = "medium"'''

A2_NEW = '''    conf = s(d.get("confidence", "")).lower()
    if conf not in {"high", "medium", "low"}:
        conf = "medium"
    # NOTE: this is only the model's self-report. answer() calls
    # _calibrate_confidence() afterwards to cap it against observable signals.'''

# ---- anchor 3: post-parse hook in answer() ----
A3 = '''    parsed = _extract_json(raw)
    if parsed is not None:
        structured = _normalize_structured(parsed)
        answer_text = structured["synthesis"] or "[Model returned structured output without a synthesis field.]"'''

A3_NEW = '''    parsed = _extract_json(raw)
    if parsed is not None:
        structured = _normalize_structured(parsed)
        structured = _calibrate_confidence(structured, r.get("top_similarity", 0.0))
        answer_text = structured["synthesis"] or "[Model returned structured output without a synthesis field.]"'''

# ---- anchor 4: insert the calibrator before answer() ----
A4 = "def answer(query: str, vault: str | None = None) -> dict:"

CALIBRATOR = '''CONF_SIM_LOW = float(os.getenv("CONF_SIM_LOW", "0.68"))
CONF_SIM_MED = float(os.getenv("CONF_SIM_MED", "0.78"))

_RANK = {"low": 0, "medium": 1, "high": 2}
_UNRANK = {0: "low", 1: "medium", 2: "high"}
_NOT_IN_NOTES = re.compile(r"\\[[^\\]]*not in (?:the )?notes[^\\]]*\\]", re.I)


def _calibrate_confidence(structured: dict, top_sim: float) -> dict:
    """Cap the model's self-reported confidence against observable signals.

    The model cannot be trusted to grade itself -- it has reported "high"
    while its own gaps list admitted the notes did not cover the question.
    This derives a ceiling from things that are actually measurable and takes
    the lower of (claimed, ceiling). The model may lower its confidence; it
    may not inflate it.

    Signals:
      top_sim  -- best semantic similarity from retrieval
      gaps     -- aspects the model itself flagged as uncovered
      markers  -- [not in notes] placeholders across the dimension items
    """
    claimed = structured.get("confidence", "medium")
    gaps = structured.get("gaps") or []

    marker_count = 0
    for items in (structured.get("dimensions") or {}).values():
        seq = items if isinstance(items, list) else [items]
        for it in seq:
            if _NOT_IN_NOTES.search(str(it)):
                marker_count += 1

    reasons = []
    ceiling = 2  # high

    if top_sim < CONF_SIM_LOW:
        ceiling = min(ceiling, 0)
        reasons.append(f"weak retrieval (top similarity {top_sim:.2f})")
    elif top_sim < CONF_SIM_MED:
        ceiling = min(ceiling, 1)
        reasons.append(f"moderate retrieval (top similarity {top_sim:.2f})")

    if gaps:
        ceiling = min(ceiling, 1)
        reasons.append(f"{len(gaps)} declared gap(s)")

    if marker_count:
        ceiling = min(ceiling, 1)
        reasons.append(f"{marker_count} value(s) not in notes")

    if len(gaps) >= 2 and marker_count >= 3:
        ceiling = min(ceiling, 0)
        reasons.append("multiple gaps and multiple unsupported values")

    final = _UNRANK[min(_RANK.get(claimed, 1), ceiling)]
    structured["confidence"] = final
    if final != claimed:
        structured["confidence_reason"] = (
            f"model claimed {claimed}; capped to {final} -- "
            + "; ".join(reasons))
    elif reasons:
        structured["confidence_reason"] = "; ".join(reasons)
    return structured


'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--revert", action="store_true")
    a = ap.parse_args()

    if a.revert:
        baks = sorted(glob.glob(TARGET + ".bak.ground2.*"))
        if not baks:
            sys.exit("no backup found -- use: git checkout generate.py "
                     "(note this also reverts the two-lane patch)")
        shutil.copy2(baks[-1], TARGET)
        print(f"restored {TARGET} from {baks[-1]}")
        return

    if not os.path.exists(TARGET):
        sys.exit(f"{TARGET} not found -- run from ~/brain/second-brain-rag")

    src = open(TARGET, encoding="utf-8").read()
    if MARKER in src:
        print("already patched -- nothing to do")
        return

    for label, anchor in (("content rules", A1),
                          ("confidence normalize", A2),
                          ("answer() post-parse", A3),
                          ("answer() signature", A4)):
        n = src.count(anchor)
        if n != 1:
            sys.exit(f"expected exactly 1 '{label}' anchor, found {n}. "
                     "Aborting rather than guessing.")

    new = src.replace(A1, A1_NEW, 1)
    new = new.replace(A2, A2_NEW, 1)
    new = new.replace(A3, A3_NEW, 1)
    new = new.replace(A4, CALIBRATOR + A4, 1)

    if not any(l.strip() == "import os" for l in new.splitlines()):
        new = new.replace("import json\nimport re",
                          "import json\nimport os\nimport re", 1)

    try:
        ast.parse(new)
    except SyntaxError as e:
        sys.exit(f"post-edit syntax error: {e} -- not writing")

    print(f"\n{TARGET}: {len(src)} -> {len(new)} chars (+{len(new)-len(src)})")
    print("\n1. GROUNDING RULE (prompt)")
    print("   numbers/vendors/roles/clauses must come from retrieved text")
    print("   [value not in notes] marker required where they do not")
    print("   explicit: does NOT license fewer items per card")
    print("\n2. DETERMINISTIC CONFIDENCE (code)")
    print("   _calibrate_confidence() caps the model's self-report against")
    print("   top similarity, declared gaps, and unsupported-value markers")
    print("   adds confidence_reason so the result is inspectable")
    print(f"\n   thresholds: low < {CONF_LOW_DEFAULT} <= medium < {CONF_MED_DEFAULT} <= high")
    print("   env: CONF_SIM_LOW, CONF_SIM_MED")

    if a.dry_run:
        print("\n--dry-run: nothing written\n")
        return

    bak = f"{TARGET}.bak.ground2.{datetime.now():%Y%m%d-%H%M%S}"
    shutil.copy2(TARGET, bak)
    open(TARGET, "w", encoding="utf-8").write(new)
    print(f"\npatched {TARGET}  (backup: {bak})")
    print("\nRestart uvicorn and re-ask the RTR question.")
    print("Expect: same card counts, invented figures replaced by markers,")
    print("confidence dropping from HIGH to medium with a stated reason.\n")


CONF_LOW_DEFAULT = "0.68"
CONF_MED_DEFAULT = "0.78"

if __name__ == "__main__":
    main()
