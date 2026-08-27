#!/usr/bin/env python3
"""
patch_numguard.py -- verify numbers against the retrieved text, in code.

WHY THIS EXISTS
---------------
The prompt-level grounding rule works about 30% of the time. In the last RTR
answer the model correctly emitted [threshold value not in notes] and
[value not in notes] in three places -- and let 800ms, 50ms, 100ms, 200ms,
XGBoost, Neural Network and "5 consecutive minutes" through unmarked.

Worse, it wrote:
    DESIGN: "auto-approve (<200), step-up (200-600), analyst hold (>600)
             [score bands from notes]"
    GAPS:   "The notes do not specify the exact score scale or band
             definitions"

It used the marker syntax to CLAIM grounding it did not have, then admitted
the gap two cards later. The model learned the vocabulary of citation without
the discipline. That is not fixable by asking more firmly -- it is the same
class of failure as self-reported confidence, and it needs the same class of
fix: computed, not requested.

WHAT THIS DOES
--------------
After the answer is parsed, every numeric token in the dimension items and the
synthesis is checked against the actual retrieved text (content lane +
practice lane). Anything whose digits appear nowhere in what was retrieved is
collected and reported.

It is deliberately PERMISSIVE -- a bare digit match anywhere in the retrieved
text counts as support. Under-flagging is preferable to crying wolf. Pure
invention like "800ms" in a corpus that never mentions 800 still gets caught.

Named identifiers are excluded by construction: B-13, E-23, pacs.008,
camt.053, ISO 20022, FIPS 203, MT202, 24/7 and bare years are not treated as
claims. Those pass because they are entities, not measurements.

Output is non-destructive. It does not rewrite the model's text. It:
  - adds one line to "gaps" listing the unverified values
  - adds "unverified_values": [...] for any UI that wants it
  - feeds the count into _calibrate_confidence so confidence drops

Requires patch_two_lane.py and patch_grounding_v2.py to be applied first.

Answer-time only. No re-stamp, no re-chunk, no re-embed.

Tuning:
    NUMGUARD=false        disable entirely
    NUMGUARD_MAX_REPORT=8 how many unverified values to list in the gap line

Usage:
    cd ~/brain/second-brain-rag
    python3 patch_numguard.py --dry-run
    python3 patch_numguard.py
    python3 patch_numguard.py --revert
"""

import argparse
import ast
import glob
import os
import shutil
import sys
from datetime import datetime

TARGET = "generate.py"
MARKER = "_flag_unverified_numbers"

A1 = "def _calibrate_confidence(structured: dict, top_sim: float) -> dict:"

GUARD = '''NUMGUARD = os.getenv("NUMGUARD", "true").lower() == "true"
NUMGUARD_MAX_REPORT = int(os.getenv("NUMGUARD_MAX_REPORT", "8"))

# A measurement claim: digits optionally followed by a unit. Deliberately
# narrow -- we want thresholds, latencies, percentages and ratios, not every
# digit that happens to appear in prose.
_NUM_CLAIM = re.compile(
    r"(?<![A-Za-z0-9.\\-/])"                     # not mid-identifier
    r"(\\d{1,3}(?:,\\d{3})+|\\d+(?:\\.\\d+)?)"      # 1,000 or 800 or 99.9
    r"\\s?"
    r"(ms|milliseconds?|seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|"
    r"%|percent|bps|x|:1|k|K|M|bn)?"
    # NOTE: '.' deliberately absent from this lookahead. Including it meant a
    # value at the end of a sentence ("...within 200ms.") failed to match and
    # slipped through unchecked. Identifiers stay safe via the LEADING
    # lookbehind, which does block a digit preceded by '.' (pacs.008).
    r"(?![A-Za-z0-9\\-/])"
)

# Tokens that contain digits but are identifiers, not measurements.
_IDENT_CTX = re.compile(
    r"[A-Za-z]-?\\d|\\d+\\.\\d+\\.\\d|"              # B-13, E-23, pacs.008
    r"\\b(?:ISO|FIPS|SP|NIST|MT|MX|pacs|camt|pain|admi|BCBS|PCI|SOC)\\b",
    re.I)


def _flag_unverified_numbers(structured: dict, retrieved: str) -> dict:
    """Collect numeric claims that do not appear in the retrieved text.

    Non-destructive: the model's wording is left alone. The finding is
    surfaced through "gaps" and "unverified_values", and the count is used
    to cap confidence.

    Permissive by design -- if the digits appear ANYWHERE in what was
    retrieved, the claim is treated as supported. The goal is to catch
    fabrication, not to litigate phrasing.
    """
    if not NUMGUARD or not retrieved:
        return structured

    # digits present in the retrieved corpus, comma-stripped
    corpus = retrieved.replace(",", "")
    corpus_digits = set(re.findall(r"\\d+(?:\\.\\d+)?", corpus))

    def _scan(text: str, found: dict):
        for m in _NUM_CLAIM.finditer(text or ""):
            raw, unit = m.group(1), (m.group(2) or "")
            window = text[max(0, m.start() - 12):m.end() + 12]
            if _IDENT_CTX.search(window):
                continue                      # B-13, pacs.008, ISO 20022...
            bare = raw.replace(",", "")
            if bare in corpus_digits:
                continue                      # supported somewhere in notes
            try:
                if not unit and 1900 <= float(bare) <= 2100:
                    continue                  # bare year
            except ValueError:
                pass
            if not unit and len(bare) <= 1:
                continue                      # "2 passes", "3 lines"
            found.setdefault(f"{raw}{unit}", 0)
            found[f"{raw}{unit}"] += 1

    found: dict = {}
    for items in (structured.get("dimensions") or {}).values():
        seq = items if isinstance(items, list) else [items]
        for it in seq:
            _scan(str(it), found)
    _scan(structured.get("synthesis", ""), found)

    if not found:
        return structured

    ordered = sorted(found, key=lambda k: -found[k])
    structured["unverified_values"] = ordered

    shown = ordered[:NUMGUARD_MAX_REPORT]
    more = len(ordered) - len(shown)
    line = ("Values stated in this answer that do not appear in the retrieved "
            "notes -- treat as unconfirmed and source them before use: "
            + ", ".join(shown)
            + (f" (and {more} more)" if more > 0 else ""))
    gaps = list(structured.get("gaps") or [])
    gaps.append(line)
    structured["gaps"] = gaps
    return structured


'''

A2 = ('        structured = _calibrate_confidence(structured, '
      'r.get("top_similarity", 0.0))')

A2_NEW = ('        structured = _flag_unverified_numbers(\n'
          '            structured, context + "\\n" + practice)\n'
          '        structured = _calibrate_confidence(structured, '
          'r.get("top_similarity", 0.0))')

# make the calibrator aware of the new signal
A3 = '''    if marker_count:
        ceiling = min(ceiling, 1)
        reasons.append(f"{marker_count} value(s) not in notes")'''

A3_NEW = '''    if marker_count:
        ceiling = min(ceiling, 1)
        reasons.append(f"{marker_count} value(s) not in notes")

    unverified = structured.get("unverified_values") or []
    if unverified:
        ceiling = min(ceiling, 1)
        reasons.append(f"{len(unverified)} unverified numeric claim(s)")
    if len(unverified) >= 5:
        ceiling = min(ceiling, 0)
        reasons.append("numeric claims largely unsupported by the notes")'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--revert", action="store_true")
    a = ap.parse_args()

    if a.revert:
        baks = sorted(glob.glob(TARGET + ".bak.numguard.*"))
        if not baks:
            sys.exit("no numguard backup found")
        shutil.copy2(baks[-1], TARGET)
        print(f"restored {TARGET} from {baks[-1]}")
        return

    if not os.path.exists(TARGET):
        sys.exit(f"{TARGET} not found -- run from ~/brain/second-brain-rag")

    src = open(TARGET, encoding="utf-8").read()
    if MARKER in src:
        print("already patched -- nothing to do")
        return

    if "_calibrate_confidence" not in src:
        sys.exit("patch_grounding_v2.py must be applied first.")
    if "_how_layer_context" not in src:
        sys.exit("patch_two_lane.py must be applied first.")

    for label, anchor in (("calibrator def", A1),
                          ("calibrate call", A2),
                          ("marker branch", A3)):
        n = src.count(anchor)
        if n != 1:
            sys.exit(f"expected exactly 1 '{label}' anchor, found {n}. Aborting.")

    new = src.replace(A1, GUARD + A1, 1)
    new = new.replace(A2, A2_NEW, 1)
    new = new.replace(A3, A3_NEW, 1)

    try:
        ast.parse(new)
    except SyntaxError as e:
        sys.exit(f"post-edit syntax error: {e} -- not writing")

    print(f"\n{TARGET}: {len(src)} -> {len(new)} chars (+{len(new)-len(src)})")
    print("\nadds _flag_unverified_numbers():")
    print("  - checks every numeric claim against the retrieved text")
    print("  - excludes identifiers (B-13, pacs.008, ISO 20022, years)")
    print("  - non-destructive: reports via gaps + unverified_values")
    print("  - feeds the count into confidence calibration")
    print("\nenv: NUMGUARD=false | NUMGUARD_MAX_REPORT=8")

    if a.dry_run:
        print("\n--dry-run: nothing written\n")
        return

    bak = f"{TARGET}.bak.numguard.{datetime.now():%Y%m%d-%H%M%S}"
    shutil.copy2(TARGET, bak)
    open(TARGET, "w", encoding="utf-8").write(new)
    print(f"\npatched {TARGET}  (backup: {bak})")
    print("\nRestart uvicorn and re-ask the RTR question.")
    print("Expect a new gap line naming 800ms / 50ms / 100ms etc,")
    print("and confidence capped with a stated reason.\n")


if __name__ == "__main__":
    main()
