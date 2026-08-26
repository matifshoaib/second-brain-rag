#!/usr/bin/env python3
"""
repair_design.py -- replace weak bsa_design fields in the AUTHORED BATCH JSONs.

Why the batches and not the vault: stamp_apply.py rebuilds ~/brain/stamped
from ~/brain/source-vault on every run, so any edit made directly to the
stamped copy is destroyed on the next stamp. The batch JSONs in
second-brain-rag/batches/ are the durable source of the how-layer. Repair
there, re-stamp, and the change persists.

Modes:
    --classify   scan every batch and report which design fields are thin
    --apply F    apply a repair file {"<note path>": "<new design text>"}

A design field is treated as ACCEPTABLE when it names an alternative
("rather than", "not X", "instead of") or lists two or more decisions
("on X, Y, and Z"). Everything else restates the note title and is queued
for repair.

Backs up every batch file it touches. Read-only unless --apply is given.

Usage:
    cd ~/brain/second-brain-rag
    python3 repair_design.py --classify
    python3 repair_design.py --classify --operational-csv ~/brain/audit-stamped.csv
    python3 repair_design.py --apply design_repairs_batch1.json
    python3 repair_design.py --apply design_repairs_batch1.json --dry-run
"""

import argparse
import csv
import glob
import json
import os
import re
import shutil
import sys
from datetime import datetime

BATCH_GLOB = "batches/batch_*.json"

# A design field is acceptable when it names WHAT must be decided, not merely
# restates the note's obligation. Signals, in order of reliability:
#
#   "decision ON <noun>"   -> names the loci of decision            (good)
#   "decision TO <verb>"   -> restates a single obligation           (thin)
#   "(a/b/c)"              -> parenthetical option list              (good)
#   "rather than", "not X" -> explicit alternative                   (good)
#   "X, Y, and Z"          -> multiple named decisions               (good)
#
# The ON/TO distinction is the strongest of these: measured on a hand-labelled
# sample it removed all 14 false repairs that the alternative-only test made,
# with no misses.
ALT = re.compile(r"\brather than\b|\bnot\b|\bversus\b|\bvs\b|\binstead of\b", re.I)
MULTI = re.compile(r",[^,]+\band\b")          # "on X, Y, and Z"
ON = re.compile(r"\bdecisions?\s+on\b|\bchoice between\b|\bdecision between\b|\btrade\b", re.I)
LIST = re.compile(r"\([^)]*[/,][^)]*\)")       # parenthetical option list
PAIR = re.compile(
    r"\b\w+\s+and\s+\w+.*\b(threshold|authority|cadence|rollback|response|"
    r"justification|testing|limits|gating|coverage|handling|sequencing|"
    r"ownership|escalation|approval|evidence)\b", re.I)

# Notes with no design decision to force. Never queue these for repair.
SKIP_PAT = re.compile(
    r"(^|/)(00-MOC|MOC)/|"
    r"Home\.md$|Vault-Index\.md$|00-Vault-Meta|"
    r"Cheatsheet\.md$|Quick.Reference|Glossary\.md$|"
    r"BUILD-TRACKER\.md$|Index\.md$|README\.md$",
    re.I)


def acceptable(text):
    return bool(ALT.search(text) or MULTI.search(text)
                or ON.search(text) or LIST.search(text) or PAIR.search(text))


def load_batches(d="batches"):
    """-> {note_path: (batch_file, block_dict)}"""
    out = {}
    for fp in sorted(glob.glob(os.path.join(d, "batch_*.json"))):
        try:
            data = json.load(open(fp, encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"[warn] {fp}: {e}", file=sys.stderr)
            continue
        data.pop("_schema", None)
        for k, v in data.items():
            if isinstance(v, dict):
                out[k] = (fp, v)
    return out


def cmd_classify(a):
    blocks = load_batches(a.blocks_dir)
    ops = set()
    if a.operational_csv and os.path.exists(a.operational_csv):
        for r in csv.DictReader(open(a.operational_csv)):
            if r.get("operational") == "True":
                ops.add(r["path"])

    keep = repair = skipped = nodesign = 0
    queue = []
    for path, (fp, blk) in sorted(blocks.items()):
        d = (blk.get("design") or "").strip()
        if not d:
            nodesign += 1
            continue
        if SKIP_PAT.search(path):
            skipped += 1
            continue
        if acceptable(d):
            keep += 1
            continue
        if ops and path not in ops:
            continue
        repair += 1
        queue.append((path, d, (blk.get("elicit") or "")))

    print(f"\n{'='*78}\nDESIGN FIELD CLASSIFICATION\n{'='*78}")
    print(f"blocks with a design field   {keep + repair + skipped}")
    print(f"  acceptable (names an alt)  {keep}")
    print(f"  skipped (MOC/index/ref)    {skipped}")
    print(f"  QUEUED FOR REPAIR          {repair}"
          + ("   (operational only)" if ops else ""))
    print(f"blocks missing design        {nodesign}\n")

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({p: {"current_design": d, "elicit": e}
                       for p, d, e in queue}, f, indent=2, ensure_ascii=False)
        print(f"repair queue written to {a.out}  ({len(queue)} notes)\n")
    else:
        for p, d, _ in queue[:40]:
            print(f"  {p}")
            print(f"      {d[:90]}")
        if len(queue) > 40:
            print(f"  ... and {len(queue)-40} more (use --out to dump all)")
        print()


def cmd_apply(a):
    repairs = json.load(open(a.apply, encoding="utf-8"))
    repairs = {k: (v if isinstance(v, str) else v.get("design"))
               for k, v in repairs.items()}
    blocks = load_batches(a.blocks_dir)

    hits, misses, touched = [], [], {}
    for path, new in repairs.items():
        if not new:
            continue
        if path not in blocks:
            misses.append(path)
            continue
        fp, blk = blocks[path]
        hits.append((fp, path, blk["design"], new))
        touched.setdefault(fp, {})[path] = new

    print(f"\nrepairs in file : {len(repairs)}")
    print(f"matched blocks  : {len(hits)}")
    print(f"unmatched paths : {len(misses)}")
    for m in misses[:10]:
        print(f"    NO MATCH: {m}")
    if misses and not a.force:
        print("\nRefusing to write with unmatched paths. Fix them, or pass --force.")
        return

    for fp, path, old, new in hits[:8]:
        print(f"\n  {path.split('/')[-1]}")
        print(f"    -  {old[:88]}")
        print(f"    +  {new[:88]}")
    if len(hits) > 8:
        print(f"\n  ... and {len(hits)-8} more")

    if a.dry_run:
        print("\n--dry-run: nothing written\n")
        return

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for fp, updates in touched.items():
        shutil.copy2(fp, f"{fp}.bak.{stamp}")
        data = json.load(open(fp, encoding="utf-8"))
        for path, new in updates.items():
            data[path]["design"] = new
        json.dump(data, open(fp, "w", encoding="utf-8"),
                  indent=2, ensure_ascii=True)
        print(f"\nupdated {fp}  ({len(updates)} blocks)  backup .bak.{stamp}")

    print("\nNext:")
    print("  python3 stamp_apply.py --vault ~/brain/source-vault "
          "--out ~/brain/stamped --blocks-dir ./batches")
    print("  python3 chunker_v2.py && caffeinate -i python3 embed_index.py")
    print("  python3 eval_retrieval.py && python3 eval_working_set.py\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks-dir", default="batches")
    ap.add_argument("--classify", action="store_true")
    ap.add_argument("--operational-csv",
                    help="audit-stamped.csv, to limit the queue to operational notes")
    ap.add_argument("--out", help="write the repair queue to this JSON")
    ap.add_argument("--apply", metavar="FILE")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    if a.apply:
        cmd_apply(a)
    elif a.classify:
        cmd_classify(a)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
