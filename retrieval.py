#!/usr/bin/env python3
"""
retrieval.py — turn a question into a set of grounded, relevant chunks.

Pipeline:
  1. Embed the query (local Ollama).
  2. Semantic search in ChromaDB (cosine).
  3. KNOW-vs-DO routing: if the query looks like "how do I...", boost the
     typed how_layer chunks so execution guidance surfaces.
  4. Graph-hop (optional): pull neighbours linked via wikilinks for context.
  5. REFUSAL GATE: if the best hit is below MIN_SIMILARITY, return nothing —
     the generator will then refuse rather than fabricate.

Exposes retrieve(query) -> dict for generate.py / app.py.
"""
import re
import httpx
import chromadb

from backend import config

_HOW_PATTERNS = re.compile(
    r"\b(how do i|how would i|how to|how should|what should i do|"
    r"steps to|approach to|elicit|specify|design|requirement|"
    r"as a bsa|what do i ask|how can i)\b",
    re.IGNORECASE,
)


def _looks_like_how(query: str) -> bool:
    return bool(_HOW_PATTERNS.search(query))


def _embed_query(text: str, client: httpx.Client) -> list:
    r = client.post(
        f"{config.OLLAMA_URL}/api/embeddings",
        json={"model": config.EMBED_MODEL, "prompt": text},
        timeout=120.0,
    )
    r.raise_for_status()
    return r.json()["embedding"]


def _get_collection():
    chroma = chromadb.PersistentClient(path=config.CHROMA_DIR)
    return chroma.get_collection(config.COLLECTION)


def _to_similarity(distance: float) -> float:
    # Chroma cosine 'distance' = 1 - cosine_similarity  ->  similarity = 1 - distance
    return 1.0 - distance


def retrieve(query: str, vault: str | None = None):
    """
    Returns:
      {
        "hits": [ {text, similarity, metadata}, ... ],   # ordered best-first
        "refused": bool,                                  # True if below gate
        "how_mode": bool,                                 # was know-vs-do routing applied
        "top_similarity": float,
      }
    """
    col = _get_collection()
    how_mode = _looks_like_how(query)

    with httpx.Client() as client:
        qemb = _embed_query(query, client)

    # optional vault scoping
    where = {"vault": vault} if vault else None

    # pull a generous candidate set; we re-rank locally
    res = col.query(
        query_embeddings=[qemb],
        n_results=max(config.TOP_K * 3, 18),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    docs   = res["documents"][0]
    metas  = res["metadatas"][0]
    dists  = res["distances"][0]

    cand = []
    for doc, meta, dist in zip(docs, metas, dists):
        sim = _to_similarity(dist)
        # KNOW-vs-DO: in how-mode, boost typed how_layer chunks
        boosted = sim
        if how_mode and meta.get("chunk_type") == "how_layer":
            boosted = sim + 0.08   # modest, deterministic nudge
        cand.append({
            "text": doc,
            "similarity": sim,        # true similarity (for the gate)
            "rank_score": boosted,    # used only for ordering
            "metadata": meta,
        })

    # order by boosted score, then keep TOP_K
    cand.sort(key=lambda x: x["rank_score"], reverse=True)
    hits = cand[: config.TOP_K]

    # REFUSAL GATE — judged on true similarity of the best hit
    top_sim = max((h["similarity"] for h in hits), default=0.0)
    if top_sim < config.MIN_SIMILARITY:
        return {"hits": [], "refused": True,
                "how_mode": how_mode, "top_similarity": top_sim}

    # GRAPH-HOP — add wikilinked neighbours of the top hits for extra context
    if config.GRAPH_HOP and hits:
        linked = set()
        for h in hits[:3]:
            wl = h["metadata"].get("wikilinks", "")
            for name in (wl.split(",") if wl else []):
                name = name.strip()
                if name:
                    linked.add(name)
        if linked:
            have = {h["metadata"].get("note_title") for h in hits}
            want = [n for n in linked if n not in have][:4]
            for title in want:
                try:
                    nb = col.get(where={"note_title": title},
                                 limit=1, include=["documents", "metadatas"])
                    if nb["ids"]:
                        hits.append({
                            "text": nb["documents"][0],
                            "similarity": None,        # context-only, not scored
                            "rank_score": None,
                            "metadata": nb["metadatas"][0],
                            "via": "graph-hop",
                        })
                except Exception:
                    pass

    return {"hits": hits, "refused": False,
            "how_mode": how_mode, "top_similarity": top_sim}


if __name__ == "__main__":
    import sys, json
    q = " ".join(sys.argv[1:]) or "how do I handle idempotency in wire payments?"
    out = retrieve(q)
    print(f"query: {q}")
    print(f"how_mode={out['how_mode']}  refused={out['refused']}  "
          f"top_sim={out['top_similarity']:.3f}")
    for h in out["hits"]:
        m = h["metadata"]
        sim = f"{h['similarity']:.3f}" if h["similarity"] is not None else "hop"
        print(f"  [{sim}] {m.get('chunk_type'):9} {m.get('note_path')}")
