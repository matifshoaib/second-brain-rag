#!/usr/bin/env python3
"""
embed_index.py — load chunks.jsonl into ChromaDB using local Ollama embeddings.

Run once after chunking (and again whenever notes change):
    python embed_index.py

Idempotent: re-running upserts by chunk_id, so changed notes update cleanly.
"""
import json, sys, time, httpx, chromadb
from chromadb.config import Settings
import config as C

def embed(texts, client):
    """Batch-embed via Ollama. nomic-embed-text returns 768-dim vectors."""
    out = []
    for t in texts:
        r = client.post(f"{C.OLLAMA_URL}/api/embeddings",
                        json={"model": C.EMBED_MODEL, "prompt": t}, timeout=120)
        r.raise_for_status()
        out.append(r.json()["embedding"])
    return out

def main():
    print(f"[index] reading {C.CHUNKS_PATH}")
    rows = [json.loads(l) for l in open(C.CHUNKS_PATH)]
    print(f"[index] {len(rows)} chunks")

    db = chromadb.PersistentClient(path=C.CHROMA_DIR, settings=Settings(anonymized_telemetry=False))
    col = db.get_or_create_collection(C.COLLECTION, metadata={"hnsw:space": "cosine"})

    http = httpx.Client()
    BATCH = 64
    t0 = time.time()
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        vecs = embed([r["text"] for r in batch], http)
        col.upsert(
            ids=[r["chunk_id"] for r in batch],
            embeddings=vecs,
            documents=[r["text"] for r in batch],
            metadatas=[{
                "vault": r["vault"],
                "note_path": r["note_path"],
                "note_title": r["note_title"],
                "section": r["section"],
                # Chroma metadata must be scalar -> join lists
                "tags": ",".join(r["tags"]),
                "wikilinks": ",".join(r["wikilinks"]),
            } for r in batch],
        )
        done = min(i+BATCH, len(rows))
        print(f"[index] {done}/{len(rows)}  ({done/(time.time()-t0):.0f} chunks/s)")
    print(f"[index] done in {time.time()-t0:.1f}s -> {C.CHROMA_DIR}")

if __name__ == "__main__":
    sys.exit(main())
