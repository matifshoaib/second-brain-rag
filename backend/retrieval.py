"""
retrieval.py — the orchestrator.

Pipeline per query:
  1. Embed query (local Ollama)
  2. Semantic search in ChromaDB (cosine), optionally filtered by vault/tag
  3. Graph-hop: pull chunks from notes wikilinked by the top hits (1 hop)
  4. Light keyword boost (re-rank chunks containing query terms)
  5. Apply refusal gate: if best similarity < MIN_SIMILARITY -> signal refusal
Returns ranked chunks with similarity + full metadata for citation.
"""
import re, httpx, chromadb
from chromadb.config import Settings
import config as C

_db = chromadb.PersistentClient(path=C.CHROMA_DIR, settings=Settings(anonymized_telemetry=False))
_col = _db.get_or_create_collection(C.COLLECTION, metadata={"hnsw:space": "cosine"})
_http = httpx.Client()

def _embed(text):
    r = _http.post(f"{C.OLLAMA_URL}/api/embeddings",
                   json={"model": C.EMBED_MODEL, "prompt": text}, timeout=120)
    r.raise_for_status()
    return r.json()["embedding"]

def _rows(res):
    out = []
    if not res["ids"] or not res["ids"][0]:
        return out
    for i, cid in enumerate(res["ids"][0]):
        dist = res["distances"][0][i]
        out.append({
            "chunk_id": cid,
            "similarity": round(1 - dist, 4),   # cosine distance -> similarity
            "text": res["documents"][0][i],
            **res["metadatas"][0][i],
        })
    return out

def retrieve(query: str, vault: str | None = None, k: int = None):
    k = k or C.TOP_K
    qvec = _embed(query)
    where = {"vault": vault} if vault else None
    hits = _rows(_col.query(query_embeddings=[qvec], n_results=k, where=where))

    # graph-hop: expand via wikilinks of the top hits (1 hop, deduped)
    if C.GRAPH_HOP and hits:
        linked = set()
        for h in hits[:3]:
            linked.update([w for w in h.get("wikilinks", "").split(",") if w])
        if linked:
            extra = _rows(_col.query(
                query_embeddings=[qvec], n_results=3,
                where={"note_title": {"$in": list(linked)[:20]}}))
            seen = {h["chunk_id"] for h in hits}
            hits += [e for e in extra if e["chunk_id"] not in seen]

    # light keyword boost
    terms = {t.lower() for t in re.findall(r"[a-zA-Z]{4,}", query)}
    for h in hits:
        kw = sum(1 for t in terms if t in h["text"].lower())
        h["score"] = h["similarity"] + 0.02 * kw
    hits.sort(key=lambda h: h["score"], reverse=True)

    best = hits[0]["similarity"] if hits else 0.0
    return {
        "refuse": best < C.MIN_SIMILARITY,
        "best_similarity": best,
        "chunks": hits[:k],
    }
