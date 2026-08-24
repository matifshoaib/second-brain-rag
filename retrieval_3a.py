#!/usr/bin/env python3
"""
retrieval.py — turn a question into a set of grounded, relevant chunks.

Pipeline (Phase 3a — HYBRID):
  1. Embed the query (local Ollama).
  2. SEMANTIC search in ChromaDB (cosine) -> top CAND_K candidates.
  3. KEYWORD search via BM25 over the same chunks -> top CAND_K candidates.
  4. RECIPROCAL RANK FUSION (RRF) merges the two ranked lists (rank-based,
     no score normalisation) -> the fused ordering.
  5. KNOW-vs-DO routing: in "how do I..." mode, the typed how_layer chunks are
     boosted *within the semantic ranking* before fusion, so execution guidance
     still surfaces (kept in rank-space, not RRF-score-space).
  6. REFUSAL GATE: judged on the best *semantic* similarity only. If it is below
     MIN_SIMILARITY we return nothing — BM25 keyword hits never rescue a chunk
     that semantic search says isn't really in the notes (faithfulness guard).
  7. Graph-hop (optional): pull wikilinked neighbours of the top hits.

If `rank_bm25` is not installed or chunks.jsonl is unavailable, retrieval
degrades cleanly to the previous semantic-only behaviour (with a one-time
warning) so the system never hard-fails on a missing dependency.

Exposes retrieve(query) -> dict for generate.py / app.py.
"""
import re
import json
import heapq
from pathlib import Path

import httpx
import chromadb

from backend import config

# --- optional keyword-retrieval dependency -------------------------------
try:
    from rank_bm25 import BM25Okapi
except Exception:                       # not installed -> semantic-only fallback
    BM25Okapi = None

# --- tunables (override in config/.env if desired) -----------------------
RRF_K          = getattr(config, "RRF_K", 60)               # RRF damping constant
CAND_K         = getattr(config, "HYBRID_CANDIDATES", 20)   # per-retriever pool
HOW_BOOST      = getattr(config, "HOW_BOOST", 0.08)         # know-vs-do nudge (rank-space)
HYBRID_ENABLED = getattr(config, "HYBRID_ENABLED", True)    # kill-switch

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


# ------------------------------------------------------------------------
# BM25 keyword index — built once, in memory, from chunks.jsonl
# ------------------------------------------------------------------------
_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list:
    """Lowercase + split on non-alphanumeric. No stemming (v1, per spec).
    NB: identifiers like 'pacs.008' / 'OSFI E-21' split into ['pacs','008'] /
    ['osfi','e','21'] — still matchable. Identifier-aware tokenisation is a
    cheap future tweak if BM25 under-weights message-type codes."""
    return _WORD_RE.findall(text.lower())


_BM25 = None            # cached {"index","ids","vaults"} | None
_BM25_TRIED = False      # so a failed/absent build only logs once


def _get_bm25():
    """Lazily build the BM25 index from chunks.jsonl and cache it.
    Returns None (and disables hybrid) if the dependency or file is missing."""
    global _BM25, _BM25_TRIED
    if _BM25 is not None or _BM25_TRIED:
        return _BM25
    _BM25_TRIED = True

    if BM25Okapi is None:
        print("[retrieval] WARN: rank_bm25 not installed "
              "(`pip install rank_bm25`); falling back to semantic-only.")
        return None

    chunks_path = Path(getattr(config, "CHUNKS_PATH", "chunks.jsonl"))
    if not chunks_path.exists():
        print(f"[retrieval] WARN: chunks file not found at {chunks_path}; "
              f"falling back to semantic-only.")
        return None

    ids, vaults, corpus = [], [], []
    for line in open(chunks_path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        c = json.loads(line)
        cid = c.get("chunk_id")
        if cid is None:
            continue
        ids.append(cid)
        vaults.append(c.get("vault", "") or "")
        corpus.append(_tokenize(c.get("text", "") or ""))

    if not corpus:
        print(f"[retrieval] WARN: chunks file {chunks_path} had no usable text; "
              f"semantic-only.")
        return None

    print(f"[retrieval] building BM25 index over {len(corpus)} chunks ...",
          flush=True)
    _BM25 = {"index": BM25Okapi(corpus), "ids": ids, "vaults": vaults}
    print("[retrieval] BM25 index ready.", flush=True)
    return _BM25


def _bm25_topk(query: str, k: int, vault: str | None) -> list:
    """Return up to k chunk_ids ranked by BM25, optionally scoped to a vault.
    Only positive-score chunks are returned (a 0 score = no token overlap)."""
    bm = _get_bm25()
    if bm is None:
        return []
    toks = _tokenize(query)
    if not toks:
        return []
    scores = bm["index"].get_scores(toks)     # aligned to bm["ids"]
    ids, vaults = bm["ids"], bm["vaults"]
    idxs = range(len(scores))
    if vault:
        idxs = [i for i in idxs if vaults[i] == vault]
    top = heapq.nlargest(k, idxs, key=lambda i: scores[i])
    return [ids[i] for i in top if scores[i] > 0.0]


def _rrf_fuse(ranked_lists, k: int = 60) -> dict:
    """Reciprocal Rank Fusion. score(id) = sum 1/(k + rank_i(id)) over the
    lists in which id appears (1-based rank). Pure rank-space; no score
    normalisation needed. Returns {chunk_id: fused_score}."""
    fused: dict = {}
    for lst in ranked_lists:
        for rank, cid in enumerate(lst, 1):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (k + rank)
    return fused


def retrieve(query: str, vault: str | None = None):
    """
    Returns:
      {
        "hits": [ {text, similarity, rank_score, rrf_score, metadata}, ... ],
        "refused": bool,            # True if best SEMANTIC sim below the gate
        "how_mode": bool,           # know-vs-do routing applied
        "hybrid": bool,             # True if BM25 fusion was active this call
        "top_similarity": float,    # best semantic similarity (gate basis)
      }
    """
    col = _get_collection()
    how_mode = _looks_like_how(query)

    with httpx.Client() as client:
        qemb = _embed_query(query, client)

    where = {"vault": vault} if vault else None

    # ---- 1) SEMANTIC candidates ----
    res = col.query(
        query_embeddings=[qemb],
        n_results=max(CAND_K, config.TOP_K),
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    sem_ids = res["ids"][0]               # Chroma always returns ids
    docs    = res["documents"][0]
    metas   = res["metadatas"][0]
    dists   = res["distances"][0]

    sem_by_id = {}
    for cid, doc, meta, dist in zip(sem_ids, docs, metas, dists):
        sem_by_id[cid] = {"text": doc, "metadata": meta,
                          "similarity": _to_similarity(dist)}

    # ---- REFUSAL GATE — best *semantic* similarity only ----
    top_sim = max((s["similarity"] for s in sem_by_id.values()), default=0.0)
    if top_sim < config.MIN_SIMILARITY:
        return {"hits": [], "refused": True, "how_mode": how_mode,
                "hybrid": False, "top_similarity": top_sim}

    # ---- semantic ranking (with know-vs-do boost folded into rank order) ----
    def _sem_key(cid):
        s = sem_by_id[cid]
        b = s["similarity"]
        if how_mode and s["metadata"].get("chunk_type") == "how_layer":
            b += HOW_BOOST
        return b
    sem_ranked_ids = sorted(sem_by_id.keys(), key=_sem_key, reverse=True)

    # ---- 2) BM25 keyword candidates ----
    bm25_ranked_ids = _bm25_topk(query, CAND_K, vault) if HYBRID_ENABLED else []
    hybrid = bool(bm25_ranked_ids)

    # ---- 3) RRF fusion (semantic-only ordering if BM25 inactive) ----
    fused = _rrf_fuse([sem_ranked_ids, bm25_ranked_ids], k=RRF_K)
    # order by fused score, tie-break on semantic similarity (deterministic)
    order = sorted(
        fused.keys(),
        key=lambda cid: (fused[cid], sem_by_id.get(cid, {}).get("similarity", -1.0)),
        reverse=True,
    )
    chosen = order[: config.TOP_K]

    # fetch text/metadata for any BM25-only ids not in the semantic set
    need = [cid for cid in chosen if cid not in sem_by_id]
    fetched = {}
    if need:
        try:
            g = col.get(ids=need, include=["documents", "metadatas"])
            for cid, doc, meta in zip(g["ids"], g["documents"], g["metadatas"]):
                fetched[cid] = {"text": doc, "metadata": meta}
        except Exception:
            pass

    hits = []
    for cid in chosen:
        if cid in sem_by_id:
            s = sem_by_id[cid]
            hits.append({"text": s["text"], "similarity": s["similarity"],
                         "rank_score": fused[cid], "rrf_score": fused[cid],
                         "metadata": s["metadata"]})
        elif cid in fetched:
            f = fetched[cid]
            hits.append({"text": f["text"], "similarity": None,   # keyword-only
                         "rank_score": fused[cid], "rrf_score": fused[cid],
                         "metadata": f["metadata"], "via": "bm25"})

    # ---- GRAPH-HOP — add wikilinked neighbours of the top hits ----
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
                            "rrf_score": None,
                            "metadata": nb["metadatas"][0],
                            "via": "graph-hop",
                        })
                except Exception:
                    pass

    return {"hits": hits, "refused": False, "how_mode": how_mode,
            "hybrid": hybrid, "top_similarity": top_sim}


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "how do I handle idempotency in wire payments?"
    out = retrieve(q)
    print(f"query: {q}")
    print(f"how_mode={out['how_mode']}  hybrid={out['hybrid']}  "
          f"refused={out['refused']}  top_sim={out['top_similarity']:.3f}")
    for h in out["hits"]:
        m = h["metadata"]
        sim = f"{h['similarity']:.3f}" if h["similarity"] is not None else (
            h.get("via", "hop"))
        print(f"  [{sim:>9}] {m.get('chunk_type'):9} {m.get('note_path')}")
