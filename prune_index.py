#!/usr/bin/env python3
"""
prune_index.py - remove vectors whose chunk_id is no longer in chunks.jsonl
(left behind when notes are renamed, moved or deleted). Pair with
embed_repair.py, which adds the chunks that are new:

    .venv/bin/python3 prune_index.py && .venv/bin/python3 embed_repair.py
"""
import json
import chromadb
from backend import config

want = {json.loads(l)["chunk_id"] for l in open(config.CHUNKS_PATH) if l.strip()}
col = chromadb.PersistentClient(path=config.CHROMA_DIR).get_collection(config.COLLECTION)
have = set(col.get(include=[])["ids"])
stale = sorted(have - want)
for i in range(0, len(stale), 500):
    col.delete(ids=stale[i:i + 500])
print(f"[prune] index had {len(have)}, chunks.jsonl has {len(want)}: removed {len(stale)} stale, "
      f"{len(want - have)} still to embed")
