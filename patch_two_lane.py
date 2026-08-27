#!/usr/bin/env python3
"""
patch_two_lane.py -- feed the dimension cards from the vault's own BSA layer.

THE PROBLEM
-----------
You have 1,347 authored how_layer blocks: curated bsa_elicit / bsa_specify /
bsa_design / bsa_dsib fields, written per note, in exactly the register the
cards need. The card generator almost never sees them. how_layer chunks are
3.2% of the store and compete in the same candidate pool as content, so they
surface in roughly 10 of 40 real questions. On the other 30 the model is asked
to invent elicitation questions while the vault's actual elicitation library
sits unretrieved.

That is why the cards read generic. Not a prompt problem, not a field-quality
problem -- the curated material is simply absent from the prompt.

THE FIX
-------
A second retrieval lane, filtered to chunk_type=how_layer, appended to the
prompt as its own labelled section. The model is told to build the cards from
that section -- adapting and combining curated blocks -- rather than composing
from scratch.

One extra vector query. NO extra LLM call. Roughly 1.1x latency.

WHAT THIS DOES NOT DO
---------------------
It does not change the synthesis, which already works well and still draws
only on the content lane. It does not touch the vault, the batches, the
chunker, or the vector store. No re-stamp, no re-chunk, no re-embed.

TUNING (env-overridable, no code edit needed)
    HOW_LANE=false      disable the lane entirely
    HOW_LANE_K=12       number of practice blocks to pull
    HOW_LANE_FLOOR=0.45 similarity floor; blocks below this are dropped

Usage:
    cd ~/brain/second-brain-rag
    python3 patch_two_lane.py --dry-run
    python3 patch_two_lane.py
    python3 patch_two_lane.py --revert
"""

import argparse
import ast
import glob
import os
import shutil
import sys
from datetime import datetime

TARGET = "generate.py"
MARKER = "_how_layer_context"

# ---- anchor 1: insert the lane function before the context builder ----
A1 = "def _build_context(hits: list) -> str:"

LANE_FN = '''HOW_LANE       = os.getenv("HOW_LANE", "true").lower() == "true"
HOW_LANE_K     = int(os.getenv("HOW_LANE_K", "12"))
HOW_LANE_FLOOR = float(os.getenv("HOW_LANE_FLOOR", "0.45"))


def _how_layer_context(query: str, vault: str | None = None) -> str:
    """Second retrieval lane -- how_layer chunks ONLY.

    The main pool is 96.8% content chunks, so the vault's curated BSA blocks
    rarely make it into the prompt. This queries for them directly so the
    cards can be built from authored practitioner material instead of being
    composed from nothing.

    Returns "" on any failure -- the lane is additive and must never break
    an answer.
    """
    if not HOW_LANE:
        return ""
    try:
        import chromadb
        from retrieval import _embed_query, _to_similarity

        col = chromadb.PersistentClient(
            path=config.CHROMA_DIR).get_collection(config.COLLECTION)

        where = {"chunk_type": "how_layer"}
        if vault:
            where = {"$and": [{"chunk_type": "how_layer"}, {"vault": vault}]}

        with httpx.Client() as _c:
            qemb = _embed_query(query, _c)

        res = col.query(
            query_embeddings=[qemb],
            n_results=HOW_LANE_K,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        if not res["ids"] or not res["ids"][0]:
            return ""

        blocks = []
        for doc, meta, dist in zip(res["documents"][0],
                                   res["metadatas"][0],
                                   res["distances"][0]):
            sim = _to_similarity(dist)
            if sim < HOW_LANE_FLOOR:
                continue
            src = meta.get("note_path", "unknown")
            blocks.append(f"--- Practice block [{sim:.2f}] from {src} ---\\n{doc}")
        return "\\n\\n".join(blocks)
    except Exception:
        return ""


'''

# ---- anchor 2: prompt assembly in answer() ----
A2 = '''    context = _build_context(r["hits"])
    prompt = (f"{SYSTEM_PROMPT}\\n\\n=== CONTEXT (the only knowledge you may use) ==="
              f"\\n{context}\\n\\n=== QUESTION ===\\n{query}\\n\\n=== JSON RESPONSE ===\\n")'''

A2_NEW = '''    context = _build_context(r["hits"])
    practice = _how_layer_context(query, vault=vault)

    practice_block = ""
    if practice:
        practice_block = (
            "\\n\\n=== BSA PRACTICE LIBRARY (curated how-layer blocks - "
            "BUILD THE CARDS FROM THESE) ===\\n" + practice)

    prompt = (f"{SYSTEM_PROMPT}\\n\\n=== CONTEXT (the only knowledge you may use) ==="
              f"\\n{context}{practice_block}"
              f"\\n\\n=== QUESTION ===\\n{query}\\n\\n=== JSON RESPONSE ===\\n")'''

# ---- anchor 3: tell the model what the new section is for ----
A3 = "- Regulatory anchors must be lifted from the notes (D-SIB Hook / bsa_dsib content)."

A3_NEW = '''- Regulatory anchors must be lifted from the notes (D-SIB Hook / bsa_dsib content).
- A "BSA PRACTICE LIBRARY" section may follow the CONTEXT. It holds curated Elicit / Specify / Design / D-SIB blocks that were authored by hand for the notes most relevant to this question. BUILD THE DIMENSION CARDS FROM THESE FIRST. Adapt, combine and sharpen them against the specific question asked -- do not copy them verbatim, and do not ignore them in favour of composing your own. They are the vault's own practitioner layer and are more reliable than anything you would invent.
- Compose a card item yourself ONLY where the practice library offers nothing relevant to that dimension. When you do, it must still be grounded in the CONTEXT.
- The practice library feeds the CARDS. The "synthesis" field still draws on the CONTEXT, not on the practice blocks.'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--revert", action="store_true")
    a = ap.parse_args()

    if a.revert:
        baks = sorted(glob.glob(TARGET + ".bak.lane.*"))
        if not baks:
            sys.exit("no two-lane backup found -- use: git checkout generate.py")
        shutil.copy2(baks[-1], TARGET)
        print(f"restored {TARGET} from {baks[-1]}")
        return

    if not os.path.exists(TARGET):
        sys.exit(f"{TARGET} not found -- run from ~/brain/second-brain-rag")

    src = open(TARGET, encoding="utf-8").read()
    if MARKER in src:
        print("already patched -- nothing to do")
        return

    for label, anchor in (("context builder", A1),
                          ("prompt assembly", A2),
                          ("content rules", A3)):
        n = src.count(anchor)
        if n != 1:
            sys.exit(f"expected exactly 1 '{label}' anchor, found {n}. "
                     "Aborting rather than guessing -- generate.py may differ "
                     "from the version this patch was written against.")

    new = src.replace(A1, LANE_FN + A1, 1)
    new = new.replace(A2, A2_NEW, 1)
    new = new.replace(A3, A3_NEW, 1)

    if "import os" not in new.split("SYSTEM_PROMPT")[0]:
        new = new.replace("import json\nimport re", "import json\nimport os\nimport re", 1)

    try:
        ast.parse(new)
    except SyntaxError as e:
        sys.exit(f"post-edit syntax error: {e} -- not writing")

    print(f"\n{TARGET}: {len(src)} -> {len(new)} chars (+{len(new)-len(src)})")
    print("\nadds:")
    print("  - _how_layer_context(): second retrieval lane, how_layer only")
    print("  - BSA PRACTICE LIBRARY section appended to the prompt")
    print("  - instruction to build cards from curated blocks, not invention")
    print("\ncost: 1 extra vector query, 0 extra LLM calls (~1.1x latency)")
    print("env:  HOW_LANE=false | HOW_LANE_K=12 | HOW_LANE_FLOOR=0.45")

    if a.dry_run:
        print("\n--dry-run: nothing written\n")
        return

    bak = f"{TARGET}.bak.lane.{datetime.now():%Y%m%d-%H%M%S}"
    shutil.copy2(TARGET, bak)
    open(TARGET, "w", encoding="utf-8").write(new)
    print(f"\npatched {TARGET}  (backup: {bak})")
    print("\nNo re-stamp, no re-chunk, no re-embed. Restart uvicorn.")
    print("\nSanity check before the UI:")
    print("  python3 -c \"import generate; "
          "print(generate._how_layer_context('what do I ask in a sanctions "
          "screening design review?')[:600])\"\n")


if __name__ == "__main__":
    main()
