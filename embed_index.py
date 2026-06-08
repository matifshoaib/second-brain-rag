#!/usr/bin/env python3
"""
embed_index.py — embed every chunk from chunks.jsonl into ChromaDB.

Reads config from backend/config.py (.env-driven). Embeddings are produced
locally by Ollama's EMBED_MODEL (nomic-embed-text). Each chunk's metadata —
including chunk_type and the bsa_* how-layer fields — is stored alongside the
vector so retrieval can filter/boost on it later.

Idempotent: re-running rebuilds the collection from scratch (drops + recreates),
so it always matches the current chunks.jsonl.

Run:  python3 embed_index.py
"""
import json, sys, time
from pathlib import Path

import httpx
import chromadb

from backend import config

import re as _re
_NOISE_CHARS_RE = _re.compile(
    r"[─-╿"   # Box Drawing
    r"▀-▟"    # Block Elements
    r"■-◿"    # Geometric Shapes
    r"]"
)
def clean_for_embed(text: str) -> str:
    """Strip pure-decoration chars (box-drawing, blocks, geometric shapes)
    that carry no semantic signal but trip some embedding models on hard 500s.
    Leaves all real punctuation, em/en dashes, and other Unicode intact."""
    return _NOISE_CHARS_RE.sub(" ", text)




def embed_one(text: str, client: httpx.Client) -> list:
    """Call Ollama's embeddings endpoint for a single chunk, with retry."""
    import time
    last_err = None
    for attempt in range(4):           # 1 initial + 3 retries
        try:
            r = client.post(
                f"{config.OLLAMA_URL}/api/embeddings",
                json={"model": config.EMBED_MODEL, "prompt": clean_for_embed(text)},
                timeout=120.0,
            )
            r.raise_for_status()
            return r.json()["embedding"]
        except Exception as e:
            last_err = e
            time.sleep(0.5 * (attempt + 1))   # 0.5s, 1.0s, 1.5s, 2.0s backoff
    raise last_err


def clean_meta(c: dict) -> dict:
    """
    Chroma metadata values must be str|int|float|bool (no None, no lists).
    Flatten what we need for filtering/boosting; drop the rest.
    """
    def s(v):
        return "" if v is None else v
    return {
        "chunk_type":  s(c.get("chunk_type", "content")),
        "vault":       s(c.get("vault")),
        "note_path":   s(c.get("note_path")),
        "note_title":  s(c.get("note_title")),
        "section":     s(c.get("section")),
        "tags":        ",".join(c.get("tags", []) or []),
        "wikilinks":   ",".join(c.get("wikilinks", []) or []),
        "bsa_stamped": bool(c.get("bsa_stamped", False)),
        "bsa_version": s(c.get("bsa_version")),
        "bsa_elicit":  s(c.get("bsa_elicit")),
        "bsa_specify": s(c.get("bsa_specify")),
        "bsa_design":  s(c.get("bsa_design")),
        "bsa_dsib":    s(c.get("bsa_dsib")),
    }


def main():
    chunks_path = Path(config.CHUNKS_PATH)
    if not chunks_path.exists():
        sys.exit(f"[embed] ERROR: chunks file not found at {chunks_path}\n"
                 f"        Run chunker_v2.py first, or fix CHUNKS_PATH in .env.")

    chunks = [json.loads(line) for line in open(chunks_path) if line.strip()]
    print(f"[embed] loaded {len(chunks)} chunks from {chunks_path}")

    # persistent Chroma on disk (CHROMA_DIR)
    Path(config.CHROMA_DIR).mkdir(parents=True, exist_ok=True)
    chroma = chromadb.PersistentClient(path=config.CHROMA_DIR)

    # fresh build: drop existing collection if present
    try:
        chroma.delete_collection(config.COLLECTION)
        print(f"[embed] dropped existing collection '{config.COLLECTION}'")
    except Exception:
        pass
    col = chroma.create_collection(
        name=config.COLLECTION,
        metadata={"hnsw:space": "cosine"},   # cosine similarity
    )

    t0 = time.time()
    BATCH = 100
    buf_ids, buf_emb, buf_doc, buf_meta = [], [], [], []

    with httpx.Client() as client:
        # quick pre-flight: confirm Ollama + embed model respond
        try:
            _ = embed_one("preflight", client)
        except Exception as e:
            sys.exit(f"[embed] ERROR: cannot reach Ollama embeddings at "
                     f"{config.OLLAMA_URL} with model {config.EMBED_MODEL}.\n"
                     f"        Is the Ollama app running? Is the model pulled?\n        {e}")

        for i, c in enumerate(chunks, 1):
            try:
                emb = embed_one(c["text"], client)
            except Exception as e:
                print(f"[embed] WARN: chunk {i} failed ({e}); skipping")
                continue
            buf_ids.append(c["chunk_id"])
            buf_emb.append(emb)
            buf_doc.append(c["text"])
            buf_meta.append(clean_meta(c))

            if len(buf_ids) >= BATCH:
                col.add(ids=buf_ids, embeddings=buf_emb,
                        documents=buf_doc, metadatas=buf_meta)
                buf_ids, buf_emb, buf_doc, buf_meta = [], [], [], []

            if i % 250 == 0 or i == len(chunks):
                rate = i / max(1e-6, (time.time() - t0))
                eta = (len(chunks) - i) / max(1e-6, rate)
                print(f"[embed] {i}/{len(chunks)}  "
                      f"({rate:.1f}/s, ETA {eta/60:.1f} min)")

        if buf_ids:
            col.add(ids=buf_ids, embeddings=buf_emb,
                    documents=buf_doc, metadatas=buf_meta)

    n = col.count()
    dt = time.time() - t0
    print(f"\n[embed] DONE — {n} vectors in collection '{config.COLLECTION}'")
    print(f"[embed] persisted at {config.CHROMA_DIR}")
    print(f"[embed] elapsed {dt/60:.1f} min")
    how = col.get(where={"chunk_type": "how_layer"}, limit=1, include=["metadatas"])
    print(f"[embed] how_layer chunks queryable: "
          f"{'yes' if how['ids'] else 'no'}")


if __name__ == "__main__":
    main()
