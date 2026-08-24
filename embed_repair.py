#!/usr/bin/env python3
"""
embed_repair.py — embed ONLY the chunks missing from the existing Chroma
collection, without rebuilding.

Use after an embed_index.py run dropped some chunks to transient Ollama 500s.
It does NOT drop the collection. It reads chunks.jsonl, finds chunk_ids not yet
present in the collection, embeds just those (reusing the deep-retry embed_one
from embed_index.py), and appends them. Fully re-runnable — run it again and it
will only attempt whatever is still missing.

Run:  python3 embed_repair.py
"""
import json, time
from pathlib import Path

import httpx
import chromadb

from backend import config
from embed_index import embed_one, clean_meta   # reuse the patched helpers


def existing_ids(col) -> set:
    """Return the set of chunk_ids already in the collection (version-robust)."""
    # Fast path: one shot (fine for tens of thousands of ids).
    try:
        return set(col.get(include=[])["ids"])
    except Exception:
        pass
    # Fallback: paginate (older/newer Chroma variations).
    ids, offset, PAGE = set(), 0, 5000
    while True:
        try:
            got = col.get(limit=PAGE, offset=offset)
        except TypeError:
            # offset unsupported -> single get of everything
            return set(col.get()["ids"])
        batch = got["ids"]
        if not batch:
            break
        ids.update(batch)
        if len(batch) < PAGE:
            break
        offset += len(batch)
    return ids


def main():
    chunks_path = Path(config.CHUNKS_PATH)
    if not chunks_path.exists():
        raise SystemExit(f"[repair] chunks file not found at {chunks_path}")

    chunks = [json.loads(l) for l in open(chunks_path) if l.strip()]
    by_id = {c["chunk_id"]: c for c in chunks}
    print(f"[repair] {len(chunks)} chunks in {chunks_path.name}")

    chroma = chromadb.PersistentClient(path=config.CHROMA_DIR)
    try:
        col = chroma.get_collection(config.COLLECTION)
    except Exception:
        raise SystemExit(
            f"[repair] collection '{config.COLLECTION}' not found at "
            f"{config.CHROMA_DIR}.\n"
            f"        Run embed_index.py first (a repair only fills gaps).")

    have = existing_ids(col)
    print(f"[repair] {len(have)} already embedded in '{config.COLLECTION}'")

    missing = [cid for cid in by_id if cid not in have]
    print(f"[repair] {len(missing)} chunk(s) missing -> embedding only these")
    if not missing:
        print("[repair] nothing to do; index already complete.")
        return

    t0 = time.time()
    ok = fail = 0
    failed_ids = []
    with httpx.Client() as client:
        for j, cid in enumerate(missing, 1):
            c = by_id[cid]
            try:
                emb = embed_one(c["text"], client)
            except Exception as e:
                fail += 1
                failed_ids.append(cid)
                print(f"[repair] STILL failing after deep retry: {cid} ({e})")
                continue
            col.add(ids=[cid], embeddings=[emb],
                    documents=[c["text"]], metadatas=[clean_meta(c)])
            ok += 1
            if j % 25 == 0 or j == len(missing):
                print(f"[repair] {j}/{len(missing)}  ok={ok} fail={fail}")

    dt = time.time() - t0
    print(f"\n[repair] DONE — ok={ok} fail={fail}")
    print(f"[repair] collection now holds {col.count()} vectors")
    print(f"[repair] elapsed {dt:.0f}s")
    if failed_ids:
        Path("repair_failed_ids.txt").write_text("\n".join(failed_ids))
        print(f"[repair] {len(failed_ids)} still failing -> repair_failed_ids.txt"
              f" (re-run embed_repair.py to retry just those)")
    else:
        print("[repair] no residual failures — index is complete.")


if __name__ == "__main__":
    main()
