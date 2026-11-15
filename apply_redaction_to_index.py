#!/usr/bin/env python3
"""
apply_redaction_to_index.py - push redacted text into the existing Chroma index
WITHOUT re-embedding.

chunk_ids are unchanged by redaction, so each changed chunk keeps its existing
vector; only the stored document and metadata are replaced. Takes ~1-2 minutes
instead of a 40-minute rebuild. Safe to re-run.
Run:  .venv/bin/python3 apply_redaction_to_index.py
"""
import json
import chromadb
from backend import config
from embed_index import clean_meta

chunks = {c["chunk_id"]: c for c in (json.loads(l) for l in open(config.CHUNKS_PATH) if l.strip())}
col = chromadb.PersistentClient(path=config.CHROMA_DIR).get_collection(config.COLLECTION)

ids = list(chunks)
changed = missing = 0
for i in range(0, len(ids), 500):
    batch = ids[i:i + 500]
    got = col.get(ids=batch, include=["documents", "metadatas", "embeddings"])
    up_ids, up_emb, up_doc, up_meta = [], [], [], []
    for cid, doc, meta, emb in zip(got["ids"], got["documents"], got["metadatas"], got["embeddings"]):
        c = chunks[cid]
        new_meta = clean_meta(c)
        if doc != c["text"] or meta != new_meta:
            up_ids.append(cid); up_emb.append(list(emb)); up_doc.append(c["text"]); up_meta.append(new_meta)
    missing += len(batch) - len(got["ids"])
    if up_ids:
        col.update(ids=up_ids, embeddings=up_emb, documents=up_doc, metadatas=up_meta)
        changed += len(up_ids)
    print(f"\r[redact] {min(i + 500, len(ids))}/{len(ids)} checked, {changed} updated", end="", flush=True)

print(f"\n[redact] done: {changed} chunks updated in place, {missing} not in index")
# Chroma's $contains is a plain substring match, so candidates are re-checked
# with whole-word rules. The terms live in the local, git-ignored redact.py.
try:
    from redact import CHECK_TERMS, CHECK_WORD
except ImportError:
    CHECK_TERMS, CHECK_WORD = (), None
left = set()
for term in CHECK_TERMS:
    got = col.get(where_document={"$contains": term}, include=["documents"])
    left |= {i for i, d in zip(got["ids"], got["documents"]) if CHECK_WORD.search(d)}
print(f"[redact] index documents still containing redacted names: {len(left)}")
