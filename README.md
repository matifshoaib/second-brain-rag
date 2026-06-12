# Second Brain

**A local-first, faithfulness-gated RAG system over a 1100-note Business Systems Analyst knowledge vault.**

> The AI is not the ceiling. The notes are.

This repository contains the **engine** — the retrieval, generation, and evaluation code. The knowledge vault it runs over (1100 hand-authored notes, ~452,643 lines, ~2.8M words across 15 sub-vaults) stays private by design. The code is public; the knowledge is not. That separation is the point: this is a system for making *your own* expert knowledge queryable, privately, on your own hardware.

---

## What this is

A Retrieval-Augmented Generation system built specifically to answer one kind of question well: not *"what is X"*, but *"how does a Business Systems Analyst at a regulated bank actually act on X"*.

It runs locally. The corpus and vector index never leave the machine. Generation is provider-swappable per query — a local model by default (unlimited, private), with a hosted model available on demand for deeper breadth. When the local notes don't cover something, the system says so rather than fabricating.

## The problem it solves

A deep personal knowledge vault is excellent at *what is X* and useless at *how do I act on X*. The operational layer a practitioner actually uses — what to ask stakeholders, what requirement something becomes, what design decision it forces, which regulatory expectation it engages — lives only in their head and gets re-derived from scratch every time.

This system closes that gap with two layers:

1. **A four-field "how-layer" ontology** authored into every note.
2. **A faithfulness-gated RAG system** designed to retrieve and reason over it.

## The how-layer ontology

Every note carries a fixed four-field execution block, authored against its real content:

| Field | What it answers |
|---|---|
| **Elicit** | What to ask stakeholders that they won't volunteer |
| **Specify** | What concrete requirement, control, or acceptance criterion this becomes |
| **Design** | What design decision or trade-off this forces |
| **Regulatory Hook** | Which specific supervisory expectation it engages |

Stored two ways: a human-readable callout for reading, and a YAML frontmatter mirror for machine retrieval. This is what turns passive reference into active, retrievable guidance.

## Architecture

```
Vault (hand-authored notes)
   │  stamp_apply.py      — idempotent four-field injection
   ▼
Stamped vault copy
   │  chunker_v2.py       — frontmatter-aware, typed how-layer chunks, force-cut fallback
   ▼
chunks.jsonl
   │  embed_index.py      — Ollama (mxbai-embed-large) → ChromaDB
   ▼
ChromaDB vector index
   │  retrieval.py        — semantic search + know-vs-do routing + graph-hop + refusal gate
   ▼
generate.py              — exhaustive synthesis + 11 analytical dimensions
   │                        (provider-swappable: local Ollama / hosted Gemini)
   │  research.py         — OPTIONAL: explicit, tagged external web research for gaps
   ▼
app.py (FastAPI)  →  ui/index.html (browser)
```

## Three properties most RAG systems don't have

1. **Faithfulness gate.** Below a similarity threshold, the system refuses to answer rather than fabricate. A confident wrong answer is worse than no answer for regulated work.

2. **Measured retrieval.** 67% Top-1 / 81% Top-K across a 21-question evaluation spanning all 15 sub-vaults. The eval harness re-runs after any change, so improvements are measured, not assumed.

3. **Tagged external research.** When local notes have gaps, an opt-in mode runs hosted generation with web-search grounding. Results land in a visually distinct, clearly-tagged panel — never blended with local-grounded content. Provenance never collapses.

## Measured results

| Metric | Value |
|---|---|
| Notes enriched with how-layer | 981 / 981 (100%) |
| Chunks indexed | 38,394 / 38,401 (99.98%) |
| Retrieval — Top-1 | 67% |
| Retrieval — Top-K | 81% |
| Embedder | `mxbai-embed-large` (335M) |
| Local generator | `qwen3:8b` |
| Hosted generator (optional) | `gemini-2.5-flash` |

The retrieval journey: an early baseline measured 38% Top-1 / 57% Top-K. Fixing an embedding-model prefix bug, then swapping to a stronger embedder with properly-tuned chunk sizing, brought it to 67% / 81%. Every step was measured against the same 21-question benchmark.

## Tech stack

- **Embeddings + local generation:** [Ollama](https://ollama.com) (`mxbai-embed-large`, `qwen3:8b`)
- **Vector store:** ChromaDB (persistent, on-disk)
- **Hosted generation + web grounding (optional):** Gemini 2.5 Flash
- **API:** FastAPI
- **UI:** single-file vanilla HTML/CSS/JS
- **Hardware this runs on:** Apple M1 Pro, 16GB unified memory

## Setup

```bash
# 1. Install Ollama and pull the models
#    (https://ollama.com)
ollama pull mxbai-embed-large
ollama pull qwen3:8b

# 2. Python environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
#    edit .env — set your paths, and optionally a GEMINI_API_KEY

# 4. Build the index over your own Markdown corpus
python3 chunker_v2.py
python3 embed_index.py

# 5. (Optional) Measure retrieval against your own eval set
python3 eval_retrieval.py

# 6. Run
python3 app.py
#    open http://localhost:8000
```

> **Note:** This repository ships the engine, not a corpus. Point it at your own Markdown notes. There is no sample vault — by design, the knowledge stays with its author.

## Honest limitations

- **The ceiling is note depth, not model quality.** A 200-word conceptual note produces a 200-word conceptual answer, regardless of model. The system is only as good as the corpus underneath it.
- **The four-field ontology breaks down on purely descriptive concepts.** A note like "What is a JWT" has no real Elicit/Specify/Design distinction; those fields end up thin.
- **External research is a single grounded call, not a research agent.** It doesn't iterate or synthesize across multiple search passes.
- **Retrieval still misses ~19% Top-K**, usually when the query term doesn't match the corpus's term for the same concept.

## Roadmap

- **Self-stamping pipeline** — auto-draft the how-layer for new notes; human reviews each.
- **Recommended Position** — a verdict-style dimension (choice + rationale + accepted cost + conditions to flip) that turns the system from descriptive to decisional.
- **Brief Generator** — produce one-page decision memos and executive talking points from any answer.
- **Multi-hop reasoning** — cross-vault chained retrieval, to answer questions that span domains.

## Author

**Muhammad Atif** *(Senior Business Systems Analyst — Lifelong Learner)*

Built on personal time, over four months, on a personal laptop. The methodology — a fixed execution ontology on top of a hand-authored knowledge base, plus a measured, faithfulness-gated RAG with explicit, tagged external research — generalizes well beyond its original domain.

## License

Released under the MIT License. See [LICENSE](LICENSE).
