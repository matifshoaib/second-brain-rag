<div align="center">

# Second Brain RAG

**A local-first retrieval-augmented generation system over a 1,348-note knowledge vault.**

Answers working questions from my own notes — not from training data — with every claim traceable to the note it came from.

![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6B35)
![Ollama](https://img.shields.io/badge/Ollama-local--first-000000)
![Top-1](https://img.shields.io/badge/Top--1-76%25-2ea44f)
![Chunks](https://img.shields.io/badge/chunks-42%2C587-5B21B6)

</div>

---

## What it is

An Obsidian vault of 1,348 interlinked notes — payments architecture, ISO 20022 and SWIFT,
financial-crime compliance, information security standards, cloud and platform engineering —
made queryable in natural language, with retrieval quality measured rather than assumed.

| | |
|---|---|
| **Notes indexed** | 1,348 across 18 topic vaults |
| **Chunks** | 42,587 — 41,240 content, 1,347 practitioner-layer |
| **Link graph** | 7,648 wikilink edges, traversed at query time |
| **Retrieval** | 76% Top-1 · 86% Top-K on a fixed 21-query evaluation set |
| **Median chunk** | 183 tokens · 85% within the 80–1,000 target band |
| **Default generation** | Local. Nothing leaves the machine unless explicitly selected. |

---

## Why build it

General assistants answer from training data. When the question is *"what does my note say
about the LYNX cut-off buffer,"* training data is the wrong source and confident invention is
the failure mode.

This system answers **only** from retrieved notes. It refuses when retrieval quality falls
below threshold, shows the source chunk behind every claim, scores its own faithfulness to
those sources, and explicitly names what the vault does **not** cover rather than filling the
gap from the model's own knowledge.

A second constraint shaped every design decision: the vault holds professional material.
Generation runs locally by default, and the cloud model is opt-in per query.

---

## Architecture

```
Obsidian vault
      │
      ▼
 stamp_apply.py     inject the practitioner layer into a working copy
      │
      ▼
 chunker_v2.py      structure-aware chunking, typed chunks   ->  chunks.jsonl
      │
      ▼
 embed_index.py     Ollama embeddings, 1024-dim              ->  ChromaDB
      │
      ▼
 retrieval.py       semantic -> refusal gate -> BM25 -> RRF -> rerank -> graph-hop
      │
      ▼
 generate.py        local or cloud synthesis, faithfulness scoring, gap detection
      │
      ▼
 app.py             FastAPI service + static UI
```

### The retrieval pipeline

Retrieval decides whether the system is useful, so it carries the most machinery.

**1 · Semantic search.** Cosine similarity over ChromaDB returns a candidate pool.

**2 · Refusal gate.** If the best *semantic* similarity falls below threshold, the system
returns nothing. Keyword hits never rescue a chunk the embedding rejected. An empty answer is
better than a confident wrong one.

**3 · BM25 keyword search.** An in-memory lexical index over the same chunks. Exact technical
tokens — `CBPR+`, `pacs.008`, `IPPROCS`, `SDN` — are precisely what dense embeddings blur.

**4 · Reciprocal Rank Fusion.** Merges the semantic and lexical rankings into one ordering.

**5 · Cross-encoder rerank.** `BAAI/bge-reranker-base` reorders the fused pool with full
query–document attention.

**6 · Know-vs-do routing.** A query classifier detects *how do I*, *what goes wrong when*, and
*how do I verify* phrasing, boosting the practitioner layer for those questions only — so
procedural queries surface applied guidance while conceptual queries surface explanation.

**7 · Graph-hop.** Follows wikilinks outward from the top hits to pull adjacent context the
embedding alone would miss. It is why a sanctions question can reach an ISO 20022 note.

### The practitioner layer

Every note carries a structured block in frontmatter, rendered as a callout in Obsidian and
indexed as its own chunk type:

```yaml
bsa_elicit:  "Ask 'how does intraday liquidity get managed against LYNX settlement,
              and what happens at gridlock or window cut-off?'"
bsa_specify: "NFR: the hub SHALL track intraday liquidity against LYNX positions and
              SHALL submit within LYNX operating windows."
bsa_design:  "Forces decisions on liquidity reservation, payment sequencing, and
              settlement-confirmation handling."
bsa_dsib:    "LYNX is a systemically important FMI under central-bank oversight;
              intraday liquidity ties to BCBS 248."
```

Separating *what a thing is* from *what to do about it* lets one note serve both a study
question and a design review, with the router deciding which layer the question wants.

### Answer surface

Every response carries a **faithfulness score** against retrieved sources, a **confidence
label**, and numbered **source cards** naming the note and section. When the vault does not
cover part of a question, the system says so under a `GAPS · NOT IN NOTES` heading rather than
filling the space — and offers to research those gaps externally, clearly tagged as
web-sourced rather than vault-sourced.

---

## Measured results

Retrieval is evaluated against a fixed query set with known-correct target notes, reported as
Top-1 (correct note ranked first) and Top-K (correct note anywhere in the returned set).

| Configuration | Top-1 | Top-K |
|---|:---:|:---:|
| Semantic only | 67% | 86% |
| **+ BM25 hybrid fusion** | **76%** | **86%** |

```bash
python3 eval_retrieval.py --md report.md
```

### Two findings worth recording

#### Hybrid retrieval was silently disabled in production

`rank_bm25` was not installed. `retrieval.py` degraded gracefully to semantic-only behind a
single warning line, so nothing looked broken — every query returned plausible results, every
evaluation run completed, and the reported accuracy was internally consistent. Half the
retrieval stack had been dark for an unknown period.

Installing the dependency recovered **9 points of Top-1 accuracy with no code change**.

The finding is not really about a dependency. It is about a system reporting success on a
configuration nobody had verified was actually running. Graceful degradation and silent
degradation are the same behaviour seen from different distances.

#### A proposed schema change was rejected on the evidence

Hypothesis: adding two fields to the practitioner layer — `failure` (how this breaks in
production) and `verify` (how to confirm the note is still true) — would improve retrieval for
diagnostic questions.

The fields were authored, stamped, chunked and embedded. Evaluation used two query groups:

- **Group A** — questions answerable *only* from the new fields
- **Group B** — regression controls answerable from unchanged note bodies

**Group A scored 1/6 Top-1 across three separate retrieval configurations** — routing off,
routing widened, BM25 enabled. Group B held at 5/6. The standing baseline was unaffected.

Cause: all fields share a single chunk, so its embedding averages across unrelated topics and
cannot win a focused diagnostic query against 41,240 content chunks. The fields cost nothing
and returned nothing.

The change was confined to the nine-note pilot and **not rolled out** to the vault.
`eval_sanctions.py` holds the A/B harness.

---

## Stack

| Layer | Choice | Rationale |
|---|---|---|
| Vector store | ChromaDB, persistent | Local, serverless, sufficient at this scale |
| Embeddings | Ollama, 1024-dim | Runs offline — vault content never leaves the machine |
| Lexical | `rank_bm25` | Exact technical tokens that embeddings blur |
| Reranker | `BAAI/bge-reranker-base` | Cross-encoder precision over a small fused pool |
| Generation, default | Ollama `qwen3:8b` | Local and private by default |
| Generation, optional | Gemini 3.5 Flash | Stronger synthesis, opt-in per query |
| API | FastAPI + uvicorn | Minimal surface, fast startup |
| Frontend | Static HTML | No build step, no framework churn |

---

## Deployment

Runs locally on `localhost:8000`.

For remote access it is published as a **private service behind Cloudflare Tunnel with Zero
Trust access control** — egress-only, no inbound ports, no static IP, and no VPN client
required on the accessing device. Authentication is enforced at the network edge before any
request reaches the application.

---

## Setup

```bash
# 1 · environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2 · configuration
cp .env.example .env
# set EMBED_MODEL, GEN_MODEL, and optionally GEMINI_API_KEY

# 3 · models
ollama serve
ollama pull "$(grep '^EMBED_MODEL=' .env | cut -d= -f2)"
ollama pull qwen3:8b

# 4 · build the index
python3 stamp_apply.py --vault <vault-path> --out <working-copy> --blocks-dir ./batches
python3 chunker_v2.py
python3 embed_index.py

# 5 · run
uvicorn app:app --port 8000
```

---

## Security posture

- **No secrets in source.** Configuration reads from environment; `.env` is gitignored.
- **Exceptions are redacted before rendering.** `httpx` embeds the full request URL in its
  exception messages, and some providers pass the API key as a query parameter — so rendering
  a raw exception leaks credentials to the browser on any upstream 5xx. `_safe_err()` strips
  credential patterns before exception text reaches the UI.
- **Vault content is gitignored.** `chunks.jsonl`, `chroma/`, and the vault working copies
  never enter version control.
- **Local by default.** Cloud generation is a deliberate per-query choice, never a fallback.

---

## Repository layout

```
chunker_v2.py        structure-aware chunking, typed chunks
embed_index.py       embedding and index construction
retrieval.py         hybrid retrieval, RRF fusion, rerank, graph-hop
generate.py          answer synthesis, faithfulness scoring, gap detection
app.py               FastAPI service and health endpoint
stamp_apply.py       practitioner-layer injection
eval_retrieval.py    retrieval evaluation harness
eval_sanctions.py    A/B harness for schema experiments
patch_router.py      self-testing patch for the query router
ui/index.html        frontend
backend/config.py    configuration
```

---

<div align="center">
<sub><b>Muhammad Atif</b> · Senior Business Systems Analyst — payments, ISO 20022, and AI assurance</sub>
</div>
