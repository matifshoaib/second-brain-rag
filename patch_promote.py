#!/usr/bin/env python3
"""
patch_promote.py -- two fixes, both diagnosed from your last run.

FIX 1: THE RETRIEVAL MISS (the real problem)
  "Real-Time Fraud Scoring.md" -- the exact note for your question, with the
  real latency budget (<300ms, single-digit-to-low-hundreds-of-ms) -- was
  found by the PRACTICE lane but absent from the CONTENT lane. So the cards
  quoted its how-layer while the synthesis, blind to the note body, invented
  800ms.

  Fix: cross-lane promotion. When a note's practice block is retrieved but
  the note has no content chunks in the main pool, pull its top 2 content
  chunks in. The how-layer becomes a router to the right notes.

FIX 2: NUMGUARD UNIT-BLINDNESS
  '800' appears somewhere in 16k chars of retrieved text, so bare-digit
  matching passed "800ms". Now a claim WITH a unit must match digits+unit
  ("800ms" / "800 ms" / "800 milliseconds") in the retrieved text; bare-digit
  fallback applies only to unitless claims. "<300ms" in the note still
  passes "300ms". Identifiers unaffected.

Requires two_lane + grounding_v2 + numguard applied. Answer-time only.

Usage: --dry-run | (apply) | --revert
"""
import argparse, ast, glob, os, shutil, sys
from datetime import datetime

TARGET = "generate.py"
MARKER = "_promote_from_practice"

A1 = '''    context = _build_context(r["hits"])
    practice = _how_layer_context(query, vault=vault)'''
A1_NEW = '''    practice = _how_layer_context(query, vault=vault)
    hits = _promote_from_practice(query, list(r["hits"]), practice, vault=vault)
    context = _build_context(hits)'''

A2 = '''        "sources": _sources(r["hits"]),'''
A2_NEW = '''        "sources": _sources(hits),'''

A3 = "def answer(query: str, vault: str | None = None) -> dict:"
PROMOTE = '''PROMOTE_NOTES  = int(os.getenv("PROMOTE_NOTES", "2"))
PROMOTE_CHUNKS = int(os.getenv("PROMOTE_CHUNKS", "2"))


def _promote_from_practice(query: str, hits: list, practice: str,
                           vault: str | None = None) -> list:
    """Cross-lane promotion: practice lane found a note the content lane
    missed -> pull that note's best content chunks into the pool.

    Measured cause: 'Real-Time Fraud Scoring.md' surfaced in the practice
    lane for the fraud-scoring question while zero of its content chunks
    made the main pool, so generation invented figures the note actually
    contains. Additive and fail-silent -- returns hits unchanged on error.
    """
    if not practice or PROMOTE_NOTES <= 0:
        return hits
    try:
        have = {h["metadata"].get("note_path") for h in hits}
        paths = re.findall(r"\\] from (.+?) ---", practice)
        missing = [p for p in dict.fromkeys(paths) if p and p not in have]
        missing = missing[:PROMOTE_NOTES]
        if not missing:
            return hits

        import chromadb
        from retrieval import _embed_query, _to_similarity
        col = chromadb.PersistentClient(
            path=config.CHROMA_DIR).get_collection(config.COLLECTION)
        with httpx.Client() as _c:
            qe = _embed_query(query, _c)

        for p in missing:
            res = col.query(
                query_embeddings=[qe],
                n_results=PROMOTE_CHUNKS + 3,
                where={"note_path": p},
                include=["documents", "metadatas", "distances"],
            )
            added = 0
            if res["ids"] and res["ids"][0]:
                for doc, meta, dist in zip(res["documents"][0],
                                           res["metadatas"][0],
                                           res["distances"][0]):
                    if meta.get("chunk_type") == "how_layer":
                        continue
                    hits.append({"text": doc, "metadata": meta,
                                 "similarity": _to_similarity(dist)})
                    added += 1
                    if added >= PROMOTE_CHUNKS:
                        break
        return hits
    except Exception:
        return hits


'''

A4 = '''            bare = raw.replace(",", "")
            if bare in corpus_digits:
                continue                      # supported somewhere in notes'''
A4_NEW = '''            bare = raw.replace(",", "")
            if unit:
                u = unit.lower()
                if u in ("ms", "millisecond", "milliseconds"):
                    alts = ("ms", "millisecond", "milliseconds")
                elif u in ("s", "sec", "secs", "second", "seconds"):
                    alts = ("s", "sec", "secs", "second", "seconds")
                elif u in ("min", "mins", "minute", "minutes"):
                    alts = ("min", "mins", "minute", "minutes")
                elif u in ("hr", "hrs", "hour", "hours"):
                    alts = ("hr", "hrs", "hour", "hours")
                elif u in ("%", "percent"):
                    alts = ("%", "percent")
                else:
                    alts = (u,)
                if any((bare + a) in corpus_norm for a in alts):
                    continue              # digits+unit found in notes
            elif bare in corpus_digits:
                continue                  # unitless claim, bare digits found'''

A5 = '''    corpus = retrieved.replace(",", "")
    corpus_digits = set(re.findall(r"\\d+(?:\\.\\d+)?", corpus))'''
A5_NEW = '''    corpus = retrieved.replace(",", "")
    corpus_digits = set(re.findall(r"\\d+(?:\\.\\d+)?", corpus))
    corpus_norm = re.sub(r"\\s+", "", corpus.lower())'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--revert", action="store_true")
    a = ap.parse_args()

    if a.revert:
        baks = sorted(glob.glob(TARGET + ".bak.promote.*"))
        if not baks:
            sys.exit("no promote backup found")
        shutil.copy2(baks[-1], TARGET)
        print(f"restored {TARGET} from {baks[-1]}")
        return

    src = open(TARGET, encoding="utf-8").read()
    if MARKER in src:
        print("already patched -- nothing to do")
        return
    for need in ("_how_layer_context", "_flag_unverified_numbers"):
        if need not in src:
            sys.exit(f"{need} missing -- apply earlier patches first")

    anchors = [("prompt assembly", A1), ("sources line", A2),
               ("answer signature", A3), ("numguard match", A4),
               ("numguard corpus", A5)]
    for label, anc in anchors:
        n = src.count(anc)
        if n != 1:
            sys.exit(f"expected 1 '{label}' anchor, found {n}. Aborting.")

    new = src.replace(A1, A1_NEW, 1).replace(A2, A2_NEW, 1)
    new = new.replace(A3, PROMOTE + A3, 1)
    new = new.replace(A4, A4_NEW, 1).replace(A5, A5_NEW, 1)
    ast.parse(new)

    print(f"\n{TARGET}: {len(src)} -> {len(new)} chars")
    print("  1. cross-lane promotion (practice lane routes content lane)")
    print("  2. unit-aware numeric guard")
    print("  env: PROMOTE_NOTES=2 PROMOTE_CHUNKS=2")
    if a.dry_run:
        print("--dry-run: nothing written\n")
        return

    bak = f"{TARGET}.bak.promote.{datetime.now():%Y%m%d-%H%M%S}"
    shutil.copy2(TARGET, bak)
    open(TARGET, "w", encoding="utf-8").write(new)
    print(f"patched  (backup: {bak})\n")


if __name__ == "__main__":
    main()
