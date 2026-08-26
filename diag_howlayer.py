#!/usr/bin/env python3
"""
diag_howlayer.py -- why do how_layer chunks not surface even when how_mode fires?

Hypothesis to test: HOW_BOOST is applied AFTER the semantic query returns
CAND_K candidates. how_layer chunks are ~3.2% of the store (1,347 of 42,587),
so in a pool of 20 you expect ~0.6 of them by chance. If the chunk is not in
the pool, no boost can rescue it -- the boost only reorders what came back.

This runs each query TWICE:
  A) normal -- what the pipeline actually returns
  B) how_layer only -- a filtered query against chunk_type=how_layer

If (B) finds a good how_layer chunk that (A) never saw, the problem is
candidate-pool composition, and the fix is a separate retrieval lane rather
than a bigger boost.

Read-only. Changes nothing.

Usage:
    python3 diag_howlayer.py
"""

import sys

QUERIES = [
    # fired how_mode in the v2 run but returned NO how_layer chunk
    "A pacs.008 was NAK'd at the network. Where do I start looking?",
    "How do I write the requirement for structured address handling before the November milestone?",
    "Payments are settling but our reconciliation shows breaks. What are the usual causes?",
    "We missed the LYNX cut-off. What happens to the payment and what do we tell the client?",
    "How do I specify the routing rules between RTM, UPM and CDM?",
    "How do I check whether our ownership and control assessment is real or just vendor data?",
    "Our screening alert volume dropped after migration. Is that good news?",
    "What do I ask in a sanctions screening design review?",
    "An auditor says our SoA is inconsistent with our risk assessment. What did we likely get wrong?",
    "What are the common reasons a nonconformity gets classified as major rather than minor?",
    "How do I build a cryptographic inventory when nobody knows where the keys are?",
    "What breaks first when you swap in a post-quantum KEM on an existing TLS path?",
    "How do I write acceptance criteria for an AI fraud-scoring model in payments?",
    "What goes wrong when a model risk framework is applied to an LLM feature?",
    "What evidence would an auditor want for an AI system in a regulated bank?",
    "What are the failure modes of an idempotency key implemented on the wrong boundary?",
    "How do I document a system for a C4 review that a regulator will also read?",
]


def main():
    import httpx
    import chromadb
    from backend import config
    from retrieval import _embed_query, _to_similarity, retrieve, CAND_K, HOW_BOOST

    col = chromadb.PersistentClient(path=config.CHROMA_DIR)\
                  .get_collection(config.COLLECTION)

    print(f"\nCAND_K = {CAND_K}   HOW_BOOST = {HOW_BOOST}")
    tot = col.count()
    n_how = len(col.get(where={"chunk_type": "how_layer"}, limit=5000)["ids"])
    print(f"how_layer chunks: {n_how} of {tot} = {n_how/tot:.1%} of the store")
    print(f"expected how_layer chunks in a random pool of {CAND_K}: "
          f"{CAND_K * n_how / tot:.2f}\n")
    print("=" * 92)

    rescued = 0
    client = httpx.Client()

    for q in QUERIES:
        out = retrieve(q)
        scored = [h for h in out["hits"] if h.get("similarity") is not None]
        in_pool = [h for h in scored
                   if h["metadata"].get("chunk_type") == "how_layer"]

        qe = _embed_query(q, client)
        r = col.query(query_embeddings=[qe], n_results=3,
                      where={"chunk_type": "how_layer"},
                      include=["documents", "metadatas", "distances"])

        best_sim = _to_similarity(r["distances"][0][0]) if r["ids"][0] else 0.0
        best_note = (r["metadatas"][0][0].get("note_path", "").split("/")[-1]
                     if r["ids"][0] else "-")
        worst_in_pool = min((h["similarity"] for h in scored), default=0.0)

        would_win = best_sim + HOW_BOOST > worst_in_pool
        if not in_pool and would_win:
            rescued += 1

        print(f"\nQ: {q[:80]}")
        print(f"   pipeline how_layer hit : {'yes' if in_pool else 'NO'}")
        print(f"   best how_layer in store: {best_sim:.3f}  {best_note[:52]}")
        print(f"   weakest chunk in pool  : {worst_in_pool:.3f}")
        print(f"   boosted how_layer      : {best_sim + HOW_BOOST:.3f}  "
              f"{'-> would enter pool' if would_win else '-> genuinely weaker'}")
        if r["ids"][0]:
            snippet = " ".join(r["documents"][0][0].split())[:150]
            print(f"   text: {snippet}...")

    print("\n" + "=" * 92)
    print(f"how_layer chunks that a separate retrieval lane would surface: "
          f"{rescued}/{len(QUERIES)}")
    print("\nIf that number is high, the fix is a dedicated how_layer query when")
    print("how_mode fires -- merged into the result set -- not a larger boost.")
    print("A larger boost cannot help a chunk that never entered the pool.\n")


if __name__ == "__main__":
    main()
