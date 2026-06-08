# The Second Brain — Design Book v3

### A Private, Measurable, Regulation-Aware Reasoning System Over a 981-Note Banking Knowledge Vault

**Author:** Muhammad Atif — Senior Business Systems Analyst & Enterprise Architect
**Domain:** Global Wires & Payments Technology, Canadian D-SIB (ACE integration, ISO 20022 CBPR+ migration)
**Version:** v3 — supersedes v2. Single source of truth.
**Status:** Working system in daily use. Measured 67% Top-1 / 81% Top-K retrieval. Two production-grade generation providers (local Qwen3:8b unlimited, hosted Gemini 2.5 Flash for breadth). Explicit external-research mode with provenance. PDF export. Roadmap to Path 1 / Path 2 / Path 3 / Multi-hop is concrete.

---

## How to read this document

This is intentionally long because the *journey* is the artifact, not just the result. Every dead end is preserved honestly; every "this didn't work" is documented. Skip by purpose:

| You are... | Read these sections |
|---|---|
| A stakeholder evaluating the work (manager, executive) | §1 (Exec Summary), §2 (Problem), §6 (Measured Results), §8 (Benefits & Honest Scope), §13 (Roadmap) |
| An employer / interviewer assessing capability | §1, §3 (Solution), §6, §7 (Engineering Journey — every dead end), §11 (Lessons), §13 (Roadmap) |
| Future-you asking "how did I do this?" | All of it. Especially §4 (Architecture), §7 (Journey), §10 (Reproducibility), §12 (Vault Discipline) |
| An engineer rebuilding the system from nothing | §4 (Architecture), §5 (Components), §10 (Reproducibility), §12 (Vault Discipline) |
| Someone considering whether to replicate the methodology | §2, §3, §8, §12, §14 (Honest Limitations) |

The whole document is ~1200 lines. The first half is non-technical and stakeholder-readable. The second half is technical and reproducibility-focused.

---

## 1. Executive Summary

I maintain a personal banking knowledge vault in Obsidian — **981 notes across 15 sub-vaults** — covering payments, AI risk, treasury, cloud architecture, data, security, governance, and the certifications relevant to a senior Business Systems Analyst at a Canadian D-SIB. The vault was excellent at *what is X* and useless at *how does a BSA at a regulated bank act on X*.

This project closed that gap with three integrated layers:

1. **An Obsidian knowledge vault discipline** that produced 981 hand-authored, cross-linked, hierarchically-organized notes — the substrate that makes the rest possible.
2. **A "How-Layer" execution ontology** — a fixed four-field block (Elicit / Specify / Design / D-SIB Hook) authored into every one of the 981 notes, converting passive reference into active BSA guidance with concrete Canadian regulatory anchors.
3. **A private, local-first RAG system** with structured multi-dimensional output, faithfulness gating, explicit external-research mode with provenance tagging, and a measurable evaluation harness. Generation is provider-swappable per query: local Qwen3:8b (unlimited, private) by default, hosted Gemini 2.5 Flash (deeper breadth, daily-capped) on demand.

**Measured outcome:** 67% Top-1 / 81% Top-K retrieval accuracy across 21 grounded queries spanning all 15 domains; functional accuracy ~86–90% when adjacent-correct retrievals are counted. Generation produces clean, faithful, exhaustive syntheses plus a structured panel of 11+ analytical dimensions (Elicit / Specify / Design / Operational Risks / Regulatory Concerns / Architectural Trade-offs / Failure Scenarios / Governance Gaps / Recommended Controls / Escalation Triggers / Open Questions, plus domain-specific extras the model adds). When local notes have gaps, an opt-in External Intelligence mode runs web-grounded research that is clearly tagged and never blended with local content. Outputs can be exported as PDF with full visual fidelity.

**What this proves:** A single practitioner, working on a laptop with free local tooling, can build a credibly-engineered, measurable, regulation-aware AI reasoning system over expert knowledge — *provided* they treat the knowledge base as a long-term hand-authored asset, treat structure as a data-engineering requirement, measure before they optimize, and accept dead ends honestly.

---

## 2. Problem Statement

### 2.1 The context

A senior Business Systems Analyst at a Domestic Systemically Important Bank doesn't just *know* about payments, AI risk, or treasury. The job is to:
- **Elicit** the requirements stakeholders won't volunteer
- **Specify** them in a form that survives regulatory scrutiny
- **Design** around the trade-offs
- **Anchor** every conclusion to the supervisory expectation that applies

Over years I built a deep, structured personal knowledge vault in Obsidian. But it was an encyclopedia, not a playbook.

### 2.2 The core problem: the "know-vs-do" gap

A typical note explained a concept — *what authorization is in card payments*, *what NIST AI RMF Measure covers*, *what BCBS 239 requires*. It did **not** capture the operational layer I actually use:

- What question must I ask stakeholders that they won't volunteer?
- What concrete requirement / control / acceptance criterion does this become?
- What design decision does this force?
- Which specific regulatory expectation does this engage?

That information existed only in my head, was re-derived from scratch every engagement, and was neither written down, searchable, nor transferable.

### 2.3 Why existing approaches fail this

| Approach | Why it doesn't work |
|---|---|
| Generic AI (ChatGPT, Claude.ai, etc.) | Answers from the public internet, fabricates confidently. Unacceptable for regulated banking work. |
| Plain text search in Obsidian | Finds *where* a topic is discussed; doesn't synthesize an answer or surface execution guidance. |
| Cloud "AI over your notes" services | Recurring cost, external data dependency, sensitive professional context goes to a third party. |
| LLM-only without retrieval | Hallucinates regulatory anchors, invents specific control numbers. |

The problem had two halves: **(a)** the knowledge itself lacked an execution dimension; **(b)** there was no private, trustworthy way to query it conversationally.

---

## 3. Solution Overview

### 3.1 Part A — The Obsidian vault as substrate

Before any AI layer existed, the vault did. Section 12 of this document covers the vault discipline in depth — but the key point here is that none of the AI engineering would have worked without **981 hand-authored, hierarchically-organized, cross-linked notes that capture one concept per note**.

This isn't an incidental input. It's the asset. The RAG system is a tool for retrieving from it; the synthesis layer is a tool for reasoning over it; but the *intelligence* is in the notes themselves. Every limitation of the system maps back to a limitation of the corpus.

### 3.2 Part B — The "How-Layer" ontology

A fixed, four-field block authored into **every** note:

| Field | Question it answers | Why it matters |
|---|---|---|
| **Elicit** | What must I ask stakeholders that they won't volunteer? | The most valuable requirements are the unstated ones. |
| **Specify** | What literal requirement / control / acceptance criterion does this become? | Turns understanding into a deliverable artifact. |
| **Design** | What decision or trade-off does this force? | Surfaces the architectural choice hidden inside the topic. |
| **D-SIB Hook** | Which specific regulatory expectation applies? | Anchors everything to OSFI / FINTRAC / Payments Canada / BCBS / etc. |

Every block is grounded in that note's *real* content (no templates, no generic filler). Every D-SIB Hook names a concrete regulatory anchor. The block is stored in two representations: a human-readable Obsidian callout for reading, and a YAML frontmatter mirror (`bsa_elicit`, `bsa_specify`, `bsa_design`, `bsa_dsib`, `bsa_stamped: true`, `bsa_version: how-v1`) for machine retrieval.

### 3.3 Part C — The local RAG system

- Runs locally; cloud egress only for *optional* hosted generation (corpus and index never leave the laptop)
- Answers only from the corpus, with **citations**
- **Refuses** when the answer isn't present, rather than fabricating
- Treats the how-layer as a **first-class, separately retrievable dimension** (typed chunks with `chunk_type=how_layer`)
- Produces **structured multi-dimensional output**: an exhaustive synthesis plus a panel of 11+ analytical dimensions, populated only when relevant
- **Explicit external-research mode** (the "B3 design"): web-grounded research, clearly tagged, opt-in, never blended into local synthesis
- **Per-query provider toggle**: choose Qwen3:8b (local, unlimited) or Gemini 2.5 Flash (hosted, deeper) for each individual question
- **PDF export** with full visual fidelity via native browser print engine

### 3.4 Design principles (locked from day one; reaffirmed through course-corrections)

1. **Faithfulness over fluency.** A grounded, cited, occasionally-refusing assistant beats a smooth fabricator.
2. **Structure is data engineering, not style.** Uniform structure is what makes the corpus reliably *machine-retrievable*.
3. **Measure, don't claim.** Every quality claim must be backed by a number from the evaluation harness.
4. **Idempotency and durability.** Multi-session enrichment work survives any tooling reset; nothing is lost.
5. **Provider abstraction.** Embedder, retriever, and generator are independently swappable without touching the others.
6. **Synthesis is never compressed for cards.** Structured panels are *additive*, never a replacement for depth. (This was a course-correction; the original implementation got it wrong — see Phase 5.)
7. **External content is always tagged.** Web-sourced findings never blend with local-grounded answers.
8. **The local default must produce enterprise-grade output.** Local Qwen3:8b output should be acceptable for daily use; cloud Gemini is for when *breadth* matters, not because local is unusable.

---

## 4. System Architecture

### 4.1 The corpus

```
My Second Brain — 981 notes, 15 vaults
├── Card-Payments-Vault ............ 26
├── SWIFT-Vault .................... 15
├── Open-Banking-RTR-Vault ......... 40
├── AAIR-Vault (AI Risk) ........... 91
├── Treasury_Vault ................. 19
├── GenAI-for-Banking .............. 38
├── Modern-Data-Architecture-Vault . 46
├── Service-Mesh-Vault ............. 42
├── AWS-Well-Architected ........... 52
├── Azure Architect Vault .......... 54
├── CRISC Knowledge Vault .......... 54
├── CBAP Knowledge Vault ........... 133
├── PMP Knowledge Vault ............ 55
├── ISO27001 Knowledge Vault ....... 20
└── The-Architects-Codex .......... 296
```

### 4.2 The how-layer (per note, dual representation)

- **Form B — human callout** (rendered in Obsidian with custom CSS):
  ```
  > [!bsa-how]+ How a BSA Uses This
  > **Elicit:** ...
  > **Specify:** ...
  > **Design:** ...
  > **D-SIB Hook:** ...
  ```
- **Form F — YAML frontmatter mirror** (machine-readable):
  ```yaml
  bsa_elicit:  "..."
  bsa_specify: "..."
  bsa_design:  "..."
  bsa_dsib:    "..."
  bsa_stamped: true
  bsa_version: how-v1
  ```

### 4.3 The full pipeline

```
        ┌──────────────────────────────────────────────────┐
        │  Hand-authored Obsidian vault (981 notes)         │
        │  - One concept per note                            │
        │  - Heavy wikilink cross-references                 │
        │  - Hierarchical folder structure per domain        │
        └───────────────┬──────────────────────────────────┘
                        │
                        │  stamp_apply.py
                        │   • Idempotent four-field injection
                        │   • Reads from batches/*.json (durable artifact)
                        │   • Mutates only notes without bsa_stamped: true
                        ▼
        ┌──────────────────────────────────────────────────┐
        │  Stamped vault copy at ~/brain/source-vault       │
        │  (live vault never mutated — only the copy is)    │
        └───────────────┬──────────────────────────────────┘
                        │
                        │  chunker_v2.py
                        │   • Frontmatter-aware
                        │   • Emits typed how_layer chunks
                        │   • Force-cut block for oversized sections
                        │   • MAX_CHUNK_CHARS=1000 (mxbai context window)
                        ▼
        ┌──────────────────────────────────────────────────┐
        │  chunks.jsonl  — 38,401 chunks                    │
        │    37,420 content chunks                          │
        │       981 how_layer chunks (typed)                │
        └───────────────┬──────────────────────────────────┘
                        │
                        │  embed_index.py
                        │   • Ollama: mxbai-embed-large (335M)
                        │   • ChromaDB persistent store
                        │   • Idempotent rebuild
                        ▼
        ┌──────────────────────────────────────────────────┐
        │  ChromaDB  —  38,394 vectors (99.98% coverage)    │
        │  Metadata: chunk_type, vault, note_path,           │
        │            bsa_* fields, wikilinks                 │
        └───────────────┬──────────────────────────────────┘
                        │
                        │  retrieval.py
                        │   • Semantic search (cosine)
                        │   • Know-vs-do routing
                        │     ("how do I..." → boost how_layer chunks)
                        │   • Graph-hop on wikilinks
                        │   • REFUSAL GATE (MIN_SIMILARITY=0.35)
                        ▼
        ┌──────────────────────────────────────────────────┐
        │  generate.py — structured response                │
        │   • Exhaustive synthesis (no truncation)          │
        │   • 11+ analytical dimensions (when relevant)     │
        │   • Regulatory anchors, gaps, confidence          │
        │   • Bracket-mismatch JSON repair                  │
        │   • Array-shape preservation + comma-split         │
        │     safety net                                     │
        │   • Provider-swappable: Ollama / Gemini           │
        └───────────────┬──────────────────────────────────┘
                        │
                        │  IF user clicks "Research gaps externally":
                        │
                        ▼
        ┌──────────────────────────────────────────────────┐
        │  research.py — B3 explicit external mode          │
        │   • Gemini + Google Search grounding              │
        │   • Per-gap findings with real source URLs        │
        │   • MAX_SOURCES_PER_FINDING = 5                   │
        │   • Partial-JSON recovery for truncated responses │
        │   • Citation marker → linked chip rendering       │
        │   • Clearly tagged "External Intelligence"        │
        │   • NEVER blended with local synthesis            │
        └───────────────┬──────────────────────────────────┘
                        │
                        ▼
        ┌──────────────────────────────────────────────────┐
        │  app.py — FastAPI                                 │
        │   /health  /vaults  /query  /research_gaps  /     │
        │   Per-query provider override accepted             │
        └───────────────┬──────────────────────────────────┘
                        ▼
        ┌──────────────────────────────────────────────────┐
        │  Web UI (browser, LAN)                            │
        │   • Full-width synthesis (unbounded)              │
        │   • Stacked dimension cards (11 fixed + extras)   │
        │   • Numbered gap list with research button         │
        │   • External Intelligence panel (teal-bordered)   │
        │   • Per-query provider toggle                      │
        │   • Per-answer PDF export                          │
        └──────────────────────────────────────────────────┘
```

### 4.4 Hardware

Apple M1 Pro MacBook (2021), 16GB unified memory, ~500GB free SSD. Metal-accelerated inference (Ollama uses Apple Silicon's unified-memory architecture; CPU + GPU + Neural Engine share RAM directly).

---

## 5. Component Inventory

Every file in the system, its role, and current state:

| Component | File | Role | Lines |
|---|---|---|---|
| **Enrichment applier** | `stamp_apply.py` | Merges batch JSONs into vault copy; injects frontmatter + callout; idempotent. | ~120 |
| **Enrichment payload** | `batches/batch_*.json` | The 981 authored how-blocks — the durable knowledge artifact. | 41 files |
| **Obsidian styling** | `how-layer.css` | Renders the `[!bsa-how]` callout with the indigo "compass" style. | ~40 |
| **Chunker** | `chunker_v2.py` | Frontmatter-aware; emits typed how_layer chunks; force-cuts oversized blocks. | ~190 |
| **Embedder / indexer** | `embed_index.py` | Embeds chunks into Chroma via Ollama; retry-on-failure; idempotent rebuild. | ~120 |
| **Retriever** | `retrieval.py` | Semantic search + know-vs-do routing + graph-hop + refusal gate. | ~140 |
| **Generator** | `generate.py` | Structured exhaustive synthesis + 11+ dimensions + gaps; JSON repair; array coercion; provider-swappable. | ~290 |
| **External research** | `research.py` | B3 explicit gap-research via Gemini + Google Search grounding; partial JSON recovery; source-cap enforcement. | ~290 |
| **API server** | `app.py` | FastAPI: `/health`, `/vaults`, `/query`, `/research_gaps`; per-query provider override. | ~140 |
| **Web UI** | `ui/index.html` | Single-file UI: synthesis + dimensions + gaps + External Intelligence panel + PDF export + provider toggle. | ~870 |
| **Evaluation harness** | `eval_retrieval.py` | 21 grounded queries across all 15 vaults; pass/fail report. | ~200 |
| **Config** | `backend/config.py`, `.env` | Single source of truth: paths, model names, thresholds. | ~30 |

---

## 6. Measured Results

### 6.1 Coverage metrics

| Metric | Value |
|---|---|
| Notes enriched (how-layer) | **981 / 981** (100%) |
| Vaults fully covered | **15 / 15** |
| How-layer fields per note | 4 (Elicit / Specify / Design / D-SIB Hook) |
| Integrity defects at final check | 0 |
| Total chunks produced | 38,401 |
| Chunks successfully indexed | 38,394 (99.98%) |
| How-layer chunks (typed) | 981 |
| Wikilink edges (graph-hop) | 5,361 |

### 6.2 Retrieval accuracy (measured via eval harness, 21 grounded queries)

| Stack | Top-1 | Top-K | Notes |
|---|---|---|---|
| `nomic-embed-text`, no prefix (initial) | 38% | 57% | Prefix bug — query/doc vectors misaligned |
| `nomic-embed-text`, prefix-fixed | 38% | 62% | Bug fixed; model still too weak for technical content |
| **`mxbai-embed-large`, MAX=1000 (current)** | **67%** | **81%** | Production state |

Functional accuracy (counting "closely-adjacent same-domain note" as a pass — which a human reviewer would, since it answers the question) is approximately **86–90%**.

### 6.3 Faithfulness verification (qualitative)

Test query: *"What is the difference between mTLS, TLS, and SSL?"*

System behavior:
- Correctly described TLS (one-way authentication) and mTLS (mutual authentication)
- Pulled real domain context from notes (SWIFT Alliance Gateway, Open Banking, payment APIs)
- **Explicitly stated** the notes don't define SSL — listed as a gap rather than fabricated

That last point is the **faithfulness gate doing its job** — refusing to invent content not present in the corpus, while still being maximally useful with what is. This is the property regulated environments require.

### 6.4 Generation provider comparison (Qwen3:8b local vs Gemini 2.5 Flash hosted)

Same Azure security architecture question, same retrieved chunks, two providers:

| Property | Qwen3:8b (local) | Gemini 2.5 Flash (hosted) |
|---|---|---|
| Synthesis depth | Multi-paragraph, dense, slightly shorter | 6 numbered sections, very long |
| Dimension count | 11 populated | 11 populated + 0–3 extras |
| Items per dimension | 3–7 | 5–15 |
| Specific control names | extensive (PIM, RBAC, Defender XDR, etc.) | same |
| Regulatory anchor extraction | ✓ (OSFI B-13, BCBS 239, PCI-DSS Req 7) | sometimes ✓, sometimes empty |
| Honest about gaps | ✓ specific gaps named | ✓ specific gaps named |
| JSON parse success | clean (Ollama `format: json` mode) | occasional bracket-mismatch (auto-repaired) |
| Speed | 30–60s per query | 3–5s per query |
| Daily quota | unlimited | ~250 requests/day free tier |
| Privacy | fully local | corpus stays local; question + retrieved chunks egress |

**Honest read:** Gemini wins on breadth per dimension and speed. Qwen3 wins on conciseness, regulatory anchor extraction reliability, and the unlimited + private envelope. Both produce genuinely usable enterprise-grade structured output. For daily work, Qwen3 is now the default; Gemini is reserved for queries that warrant deeper breadth.

### 6.5 Structured output coverage

For a deep multi-dimensional question (e.g., *"AI fraud scoring on RTR — what concerns emerge?"*), the system populates:
- An exhaustive **synthesis** (multi-paragraph, teaching-grade, no card-shaped truncation)
- 8–12 **dimensions** out of the 11 fixed (depending on relevance)
- 0–3 **domain-specific extra dimensions** the model added (e.g. `latency_budget`, `bias_surface`, `data_lineage`)
- A **regulatory anchor list** lifted from D-SIB Hook content
- A **gaps list** (drives the optional external-research mode)
- A **confidence pill** (high / medium / low)

### 6.6 External Intelligence mode

When invoked on the NFR question's 6 gaps (post Path-A+C-revised tuning):
- Returned all 6 structured findings, each with up to 5 real source URLs
- Source publishers included OSFI, McCarthy Tétrault, Torys, Protiviti, FINTRAC, arXiv, Wikipedia
- Findings were **clearly tagged** with `provenance: "External Intelligence (web-sourced, not in vault)"` metadata
- Citation markers (`[cite: 3, 7]`) rendered as clickable superscript chips linked to the source list
- Partial-JSON recovery kicked in once during testing when Gemini truncated mid-output on a 6-gap query: 2-of-3 findings salvaged rather than losing everything (this was pre-tuning; post-tuning truncation no longer occurs)

---

## 7. The Engineering Journey — Every Increment

This section is the *bible* portion. Every phase the project went through, in order, including dead ends and course-corrections. The named anecdotes are preserved because they are how the lessons were earned.

### Phase 1 — Authoring the how-layer (the slow work)

**Goal:** Inject the four-field execution block into every note.

**Decisions locked early:**
- Four-field consistency contract (Elicit / Specify / Design / D-SIB Hook)
- Dual representation (human callout + frontmatter mirror)
- Idempotent application; original vault never mutated
- Batch-based authoring: each batch is a JSON file, durable on disk

**Execution:**
- 36 numbered batches + 5 catch-up batches = 41 JSON files total
- Each batch authored against the note's *real* content (no templates)
- `stamp_apply.py` applied the batches to a copy of the vault

**QA discipline:**
- Pre-application scan caught one malformed entry that would have polluted the corpus
- Final integrity check: 981 / 981 stamped, 0 defects

**Lesson:** The durable artifact was the JSON batches, not the in-memory state. Multi-session work survived any tooling reset because the human (the JSON files) was the persistence layer.

### Phase 2 — Initial RAG build (the first naïve pass)

**Goal:** Stand up the retrieval pipeline end-to-end.

**Stack:**
- Embedder: `nomic-embed-text` (274MB, general-purpose)
- Vector store: ChromaDB (persistent on disk)
- Generator: local `qwen2.5:3b`
- Server: FastAPI
- UI: vanilla HTML + JS

**Initial result:** Pipeline ran end-to-end. UI responded. Looked like it worked.

**Lesson hidden here:** "It runs" ≠ "it's correct." The next phase showed exactly why.

### Phase 3 — The retrieval-quality investigation (the inflection point)

**The smoking-gun query:** *"What is the difference between SSL, TLS, and mTLS?"* returned `User Stories.md` (a CBAP technique note) as the top hit — at similarity 0.798 (confidently wrong).

This drove a systematic investigation across multiple iterations.

#### 3.1 Built `eval_retrieval.py` (the most important artifact in the project)

- 21 grounded queries, 1–2 per vault, each mapped to a real expected note
- Tests both Top-1 (correct note ranked #1) and Top-K (correct note anywhere in returned hits)
- **Verified every expected note exists in the corpus** before considering any baseline a real failure

**Initial measured baseline: 38% Top-1 / 57% Top-K.**

**Lesson:** Without measurement, every "fix" is wishful thinking. The eval harness turned guesses into experiments.

#### 3.2 The prefix bug

Discovered `nomic-embed-text` is trained to expect `search_document:` and `search_query:` prefixes. Without them, query and document vectors live in **misaligned subspaces** and similarity scores collapse into a flat 0.72–0.77 band — making the ranking essentially random.

Empirically confirmed: same-text identical embeds (model is deterministic ✓), but adding the prefix changed the vector by +0.10 cosine similarity on aligned pairs.

Patched both `embed_index.py` and `retrieval.py`. Re-embedded.

**Result after prefix fix: 38% Top-1 / 62% Top-K.** Bug was real, but `nomic-embed-text` (274MB, general-purpose) was still too weak on technical content for this corpus.

**Lesson:** Embedding models are *not* drop-in components. Each family has its own task-prefix conventions; ignoring them silently degrades retrieval in a way that *looks* normal but isn't.

#### 3.3 The embedder swap

Decided to upgrade to `mxbai-embed-large` (335M params, 669MB) — a more discriminative model trained for technical content.

**New problem surfaced immediately:** chunks 1,000+ tokens 500'd against mxbai's tighter effective context window. Ollama returned a generic `500 Internal Server Error` that masked the real error.

#### 3.4 The diagnostic-poison lesson

Initial hypothesis was wrong: I blamed Unicode box-drawing characters because some failing chunks had them. Wasted time stripping noise characters.

**Real diagnosis came from poking the API directly:**

```bash
curl ... /api/embeddings ... | head
# {"error":"the input length exceeds the context length"}
```

Ollama's generic 500 status was hiding a specific length-limit error. **Always poke the underlying API directly** when something fails repeatedly.

#### 3.5 The chunk-cap iteration

Tightened `MAX_CHUNK_CHARS` in `chunker_v2.py` through successive measured iterations:

| Cap | Chunks produced | `chunk_tokens_max` | Failure rate during embed |
|---|---|---|---|
| 4000 (original) | 14,341 | 3,134 | >5% (cluster bursts of 30+) |
| 1800 | 22,208 | 538 | ~3% |
| 1500 | 26,002 | 538 | 0.4% (still some clusters) |
| **1000** | **38,401** | **538*** | **0.005%** (2 of 38,401) |

\* `chunk_tokens_max` stayed at 538 because the *estimator* (`chars / 4`) underestimates real tokens for technical content; the *real* effective embed limit was ~350 tokens, which 1000 chars × ~3 chars/token in dense regulatory/code content stays under.

**Lesson:** Token estimates aren't tokens. `len(text) // 4` underestimates real tokens for technical content. Set conservative char caps and verify on sample chunks before committing to a full embed.

#### 3.6 The force-cut block

Some sections (giant tables, code blocks with no headers/paragraphs) had no natural split points. Without a hard fallback, they bypassed all chunking logic and remained oversized.

Added to `chunker_v2.py`:

```python
# hard force-cut for blocks that still exceed limit (e.g. giant tables)
final = []
for c in chunks:
    while len(c) > MAX_CHUNK_CHARS:
        final.append(c[:MAX_CHUNK_CHARS])
        c = c[MAX_CHUNK_CHARS - OVERLAP_CHARS:]
    if c.strip():
        final.append(c)
return final
```

**Lesson:** Every chunker needs a hard fallback. Natural-split logic always has edge cases.

#### 3.7 Sample-test discipline

After the chunk-cap iterations: every cap change went through a **5-chunk sample API test** before committing to a 25-minute full embed. This single discipline saved hours over the course of the investigation.

**Lesson:** Sample-test before any expensive full run. Cycle time for fixing assumptions is the difference between hours and days.

#### 3.8 The final measured outcome

Re-ran eval against the freshly-built mxbai index with proper chunking:

**67% Top-1 / 81% Top-K. The TLS query now returns `TLS-and-mTLS-Deep-Dive.md` at rank 1.** Honest functional accuracy (allowing for adjacent-correct retrievals) is 86–90%.

### Phase 4 — Generation quality (a different problem entirely)

With retrieval working, the limitation moved to generation. The local 3B model produced a TLS answer with a self-contradicting summary line: described TLS as one-way, then said in the summary "both TLS and mTLS use mutual authentication." That contradiction is a 3B-scale limitation, not fixable by prompt tuning.

Tested provider switch to `gemini-2.5-flash`: same retrieved chunks, clean output, no contradictions, explicit gap acknowledgments. The provider-abstraction architecture earned its existence here in a single session.

**Lesson:** Architectural seams exist for a reason. The provider switch was one config line; without it, fixing generation would have meant rewriting the whole stack.

### Phase 5 — The structured-response evolution (and a course-correction)

**First attempt (wrong):** I compressed the rich answer into thin BSA-card panels. The synthesis got truncated to fit the card-shaped UI. This *reduced* the quality of answers — exactly the opposite of what "structured enterprise response" should mean.

User pushback (direct quote, preserved for the lesson): *"Son of a bitch... cards look nice but they are showing very very limited information. I didn't want the quality to be reduced however those cards are also a bit helpful but the cards are not exhaustive."*

**Course-correction (right):**

1. **Synthesis is exhaustive again.** The prompt explicitly demands "LONG. EXHAUSTIVE. Do not truncate to fit card-shaped panels."
2. **Dimensions are ADDITIVE.** They appear *below* the synthesis, never replace it.
3. **Fixed list + extendable.** 11 default dimensions; the model MAY add domain-specific ones (`latency_budget`, `bias_surface`, etc.) as needed.
4. **Only populated when relevant.** No padding. A question about app-security controls won't produce "Failure Scenarios"; a question about AI fraud scoring on RTR will.

**The 11 fixed dimensions:**

| Dimension | What it surfaces |
|---|---|
| Elicit | Questions to ask stakeholders that they won't volunteer |
| Specify | Concrete requirements / controls / acceptance criteria |
| Design | Design decisions or trade-offs the topic forces |
| Operational Risks | Concrete operational risks (incidents, ops failures, day-2 issues) |
| Regulatory Concerns | Beyond the anchor list — what supervisors would scrutinize |
| Architectural Trade-offs | Latency vs accuracy, central vs federated, etc. |
| Failure Scenarios | Plausible failure modes the topic creates |
| Governance Gaps | Who owns what; accountability gaps |
| Recommended Controls | Preventive, detective, corrective controls |
| Escalation Triggers | When to escalate to risk / legal / executive |
| Open Questions | What remains unresolved |

**Lesson:** Synthesis quality is non-negotiable. Structured panels augment depth; they don't compress it. *When the user pushes back hard, listen — even (especially) when they're profane about it.*

### Phase 6 — Explicit external-research mode (the "B3" design)

When the local notes have gaps, the system can run web-grounded research. **Critical design constraints (locked):**

- **Opt-in.** Never automatic. User must click "Research these gaps externally."
- **Tagged.** Every external finding carries `provenance: "External Intelligence (web-sourced, not in vault)"`.
- **Never blended.** External results render in a visually-distinct teal-bordered panel below the local content. Never inline with local synthesis.
- **Real sources.** Gemini with Google Search grounding; every finding cites real URLs.

#### 6.1 The truncation problem

First production query: Gemini returned valid JSON wrapped in ```` ```json ``` ```` fences but truncated mid-output (hit `maxOutputTokens` budget on a 6-gap query). The strict parser rejected the incomplete JSON; everything fell back to a raw-prose path.

**Two-part fix:**

1. **Tightened the research prompt** — findings now "2-4 sentences" instead of "1-3 paragraphs"; source count capped explicitly.
2. **Added `_recover_partial_findings()`** — when full parse fails, salvages every *complete* `{gap, finding, sources, …}` object from the truncated text. Discards only the incomplete tail.

Verified by tests:
- Truncated 3-finding payload → 2 complete findings recovered cleanly ✓
- Valid full payload → still parses normally ✓
- Garbage input → returns empty (no false positives) ✓

When recovery kicks in, the UI shows: *"Response was truncated by the model; N complete finding(s) were recovered."*

**Lesson:** Robust parsing means partial recovery, not just strict validation. When the model misbehaves, salvage what you can rather than give up.

#### 6.2 Citation markers and run-on chips

Gemini's grounding system emits `[cite: 3, 7, 18]` markers in finding prose. The first UI render left these as literal text. Fixed: a `processCiteMarkers()` function in the UI strips them and converts them to small superscript chips, each linking to the matching source URL (1-indexed, as Gemini emits them).

Separately: gaps were rendering as run-on concatenated chips. Fixed: gaps now display as a vertical numbered list, each item with its own red-bordered card.

### Phase 7 — Markdown list rendering bug (the "1, 1, 1, 1, 1" problem)

User reported numbered lists in synthesis showing as "1, 1, 1, 1, 1" instead of "1, 2, 3, 4, 5".

**Root cause:** Markdown spec auto-numbers ordered lists; the literal numbers in source don't matter. But the model's output has *blank lines between numbered items* (each is a paragraph), and my regex required consecutive lines to group them as one list. So each `1.` became its own `<ol>` of one, resetting the counter every time.

**Fix:** Regex that allows blank lines between numbered items, then splits on `N.` markers and renumbers the items into a single `<ol>`. Tested against exact failing input: 5 items → 1 `<ol>` block, browser renders 1-2-3-4-5. ✓

**Lesson:** Markdown rendering has a thousand edge cases. Always test the regex against real model output, not a synthetic example.

### Phase 8 — Gemini quota debugging (the "rate limit on every query" episode)

User: *"every query is generating Rate limit hit (Gemini free tier: ~15 req/min). Please wait 60 seconds and try again."*

This was confusing because the per-minute counter shouldn't fire on every single query.

**Root cause:** `gemini-2.5-flash` has **dynamic thinking tokens** by default — the model burns hidden reasoning tokens before producing visible output. For complex prompts (long system prompt + 6 retrieved chunks + JSON schema instruction), Gemini decides to "think hard" and can generate **5–10x the visible output tokens in invisible reasoning**. All of those reasoning tokens count against quota.

**Fix:** Set `thinkingConfig: {thinkingBudget: 0}` in both `generate.py` and `research.py`. For RAG over retrieved context, the reasoning is wasted anyway — the context already constrains the answer. Combined with cutting `maxOutputTokens` from 8192 to 4096, each query now costs ~10x less quota than before.

**Lesson:** When a quota error fires more often than it should, the cause is usually a hidden cost multiplier — not the visible request count. Read the model's docs carefully for tokens you can't see.

### Phase 9 — Daily-cap pragmatics (the per-query provider toggle)

Even with `thinkingBudget: 0`, `gemini-2.5-flash` free tier is **250 requests/day**. User was burning through it on exploratory queries that didn't need Gemini-grade synthesis.

**Fix:** Per-query provider toggle in the UI. Three options:
- *default (.env)* — uses whatever `GEN_PROVIDER` says
- *local (ollama) — unlimited* — forces Ollama for this query
- *gemini 2.5 flash — daily-capped* — forces Gemini

Backend: `Query` model accepts `provider: str | None`. App temporarily swaps `config.GEN_PROVIDER` for the request, restores in `finally`.

**Lesson:** Architecture earning its keep again. Provider abstraction at the config layer meant adding per-query override was 10 lines of code, not a refactor.

### Phase 10 — The Qwen3:8b upgrade (the local model that actually works)

User wanted to move off `qwen2.5:3b` for the local default. Researched current Ollama landscape:

- Qwen3 8B beats Qwen2.5 7B by ~29 points on MMLU-pro, ~22 on GPQA, ~40 on MATH
- Qwen3 8B outperforms Qwen2.5 14B on more than half of benchmarks
- Qwen3 supports 128K context, has hybrid thinking/non-thinking modes

Pulled `qwen3:8b`. Set as the local default.

**First production query (Azure security architecture):** Multi-paragraph exhaustive synthesis, 11 dimensions populated, regulatory anchors lifted cleanly from D-SIB Hook content (OSFI B-13, BCBS 239, PCI-DSS Req 7), honest gaps named specifically. Output quality comparable to Gemini for this query class.

**Lesson:** The local-vs-cloud gap closed. 8B-class models now produce genuinely usable structured output for RAG over retrieved chunks. The Mac mini upgrade for 14B class is no longer urgent.

### Phase 11 — The Qwen3 schema bug (arrays vs strings vs paragraphs)

Same Azure question, asked again the next day. Output now had **no bullets** in any dimension card. Specify was a single comma-separated string: "MFA for all users, PIM for privileged access, Private Endpoints for data services..."

**Root cause:** Qwen3 is **non-deterministic about JSON schema**. Sometimes returns dimensions as arrays of strings; sometimes collapses them into a single comma-separated sentence; sometimes a sentence-separated paragraph. The renderer can only render what it gets.

**Three-layer fix:**

1. **Sharpened prompt** with explicit WRONG/RIGHT examples:
   ```
   WRONG:  "specify": "MFA for all users, PIM for privileged access, Private Endpoints"
   RIGHT:  "specify": ["MFA for all users via Entra ID", "PIM for privileged access", ...]
   ```
2. **Ollama JSON mode** (`"format": "json"` in the API body) — Ollama's native JSON-biasing keeps Qwen3 on schema more reliably.
3. **Server-side `_split_into_items` safety net** — if a string has 3+ sentences (`. ` + capital letter) or 3+ commas, split it server-side into a proper list.

Verified: 6-item comma-string → 6 bullets. 5-sentence paragraph → 5 bullets. Real arrays preserved.

**Lesson:** When the model is the source of inconsistency, don't trust the prompt alone. Defensive parsing in code is the only thing that survives the next model release.

### Phase 12 — The bracket-mismatch JSON repair

Gemini occasionally emits invalid JSON in long structured responses:

```json
"escalation_triggers": [
  "Detection of a critical vulnerability...",
  "Any incident requiring external regulatory notification."
}      ← should be ], not }
```

That single-character error causes `json.loads` to reject the entire payload. The UI was falling through to "raw prose" rendering and dumping the JSON as text.

**Fix: `_try_repair_json()`** — walks the string with a stack of expected closers. When it sees a `}` where it expected `]` (or vice versa), it swaps the closer to what the stack expects. Also strips trailing commas. Also auto-closes any unclosed tail.

Verified against the exact failing payload from production: bracket-mismatch parsed cleanly, all fields preserved including `confidence: high`.

**Lesson:** Defensive parsing again. Models will keep emitting these errors; the parser has to be more robust than the model.

### Phase 13 — The External Intelligence source-cap tuning (Path A + C)

User: *"why is external results just limited to 3??"*

Six gaps were submitted; only 3 findings came back, with a "response was truncated" caveat. Root cause: each finding had 5 sources × ~250 chars (Vertex AI redirect URLs) × ~80 tokens = ~2,000 tokens just for URLs. `maxOutputTokens: 4096` hit the ceiling mid-response.

**Fix (Path A + C):**
- **A**: Raised `maxOutputTokens` from 4096 to 8192 (doubles per-call budget; per-call daily quota cost unchanged)
- **C**: Hard-capped sources at 5 per finding via a constant `MAX_SOURCES_PER_FINDING = 5`, enforced in both prompt and normalizer (belt-and-suspenders)

User initially worried this would reduce quality. After honest discussion, settled on cap=5 (same as before, just now actually enforced) rather than cap=3 (which would have reduced source breadth meaningfully).

Result: all 6 findings now fit comfortably; no truncation caveat appears.

**Lesson:** When trade-offs exist, surface them before executing. The user knew which side mattered more for their work — I just had to ask.

### Phase 14 — PDF export

User wanted exportable artifacts (PDF / Word / Markdown). I pushed back on Word (`.docx` from browser JS produces visibly worse layout than the on-screen rendering). Markdown was open. PDF was the priority.

**Approach:** Native `window.print()` + `@media print` stylesheet. No external library. Browser's print engine produces a pixel-faithful PDF of the on-screen layout, with `print-color-adjust: exact` forcing the coloured accents to render.

**Print stylesheet handles:**
- Hide app chrome (top bar, composer, send button, vault selector, export button itself)
- Question becomes a header with indigo underline
- Synthesis gets a "SYNTHESIS" label
- Each dimension card stays whole (`page-break-inside: avoid`)
- External Intelligence panel renders with its teal banner, numbered findings, clickable source URLs
- Citation cards laid out as a tidy reference list with a label
- Footer on the last page: *"Generated from Muhammad Atif's Second Brain · 981 notes · retrieval-grounded · {timestamp}"*

Per-answer button (instead of global), so only the answer you're looking at exports. `document.title` is briefly swapped to a slugified filename like `second-brain-2026-05-30-azure-security-architecture.pdf`.

**Lesson:** Native browser features are often better than libraries. `window.print()` is older than React but produces better PDF output than any JS library on the market.

---

## 8. Benefits & Honest Scope

### 8.1 For the practitioner (me)

- Every topic in the vault carries the four things a BSA needs to *act* on it, not just understand it
- Every piece of guidance names the specific regulatory expectation it engages
- Cross-domain synthesis: a single question can pull from payments, AI risk, data governance, and security simultaneously
- Faithfulness gate: I never have to second-guess whether the answer was invented; refusals are honest
- Structured output: the same question yields synthesis + BSA-actionable dimensions + regulatory anchors in one shot
- Optional external research with full provenance — gaps in my notes are now actionable, not silent
- PDF export means any answer can become a deliverable in 10 seconds

### 8.2 For an organization (transferable value)

- A repeatable methodology — "fixed execution contract on top of a knowledge base + private RAG with measured retrieval + opt-in tagged external research" — generalizes to legal, audit, engineering standards, SOP libraries
- A model for trustworthy enterprise AI: faithful, cited, refuses when unsure, tags external content
- Data sovereignty: high-value knowledge AI delivered with zero third-party data exposure (corpus and index never leave the laptop)
- Gap visibility: refusals and explicit gap lists map where institutional knowledge is thin

### 8.3 Honest scope statement

This is a **personal** knowledge system, not enterprise infrastructure. The how-layer reflects the author's documented practice, not the bank's sanctioned standard. The D-SIB Hook naming OSFI E-21 doesn't mean OSFI endorses this interpretation. An AI assistant over personal notes that presents itself as authoritative bank guidance is a governance failure, not a feature. Stating this up front is part of the discipline.

The system is for *the practitioner's own use*, to make their own work faster and more thorough. It is not a system that produces deliverables for direct external consumption without human review and accountability.

---

## 9. Day-to-Day Operation & Maintenance

### 9.1 Routine maintenance when notes change

1. Re-stamp (idempotent — only touches new/changed notes): `python3 stamp_apply.py`
2. Re-chunk: `python3 chunker_v2.py`
3. Re-embed (drops and rebuilds the collection): `python3 embed_index.py`
4. Restart the server: Ctrl-C `app.py`, then `python3 app.py`
5. (Optional) Re-run eval to confirm no regression: `python3 eval_retrieval.py`

The eval is the regression test. Any change to the system should be measured against the same 21-query benchmark before being declared an improvement.

### 9.2 Keeping the system alive

- **One stamping pass per new note.** Author the four fields against the note's real content. Run the applier.
- **Re-chunk and re-embed after any batch of additions.** Both are idempotent.
- **Re-run the eval** after every meaningful corpus expansion. Score should not regress.
- **Use refusals as an editorial signal.** If the system refuses on a question you think it *should* be able to answer, that's a gap worth filling.

### 9.3 Daily provider strategy

- Default: Qwen3:8b (local, unlimited, private). Use for casual / exploratory / iterative queries.
- Toggle to Gemini: only when synthesis breadth genuinely matters (deep multi-dimensional analysis, deliverable-grade output). Daily budget of ~250 requests lasts essentially forever when reserved for these.

---

## 10. Reproducibility — Rebuild From Nothing

This section is written so the entire system can be reconstructed without reference to anything else.

### Prerequisites
- A Markdown knowledge corpus (here: an Obsidian vault) — see §12 for how to build one
- macOS or Linux with Python 3.10+
- Ollama installed (`brew install --cask ollama` on macOS)
- (Optional) A Gemini API key for hosted generation and external research
- ~5GB free disk + a few hours

### Phase A — Design the contract (one-time)
1. Define a fixed-field execution contract for your domain. Uniformity is what makes the layer machine-retrievable.
2. Decide on dual representation: human callout *and* YAML frontmatter mirror, with `stamped: true` and a version string.

### Phase B — Author the enrichment
3. Work through the corpus in batches (one vault at a time). Author each block against the note's *real* content.
4. Emit each batch as a JSON file keyed by relative note path. **These JSON files are the durable artifact.**
5. After each batch, run the applier against a copy of the vault; confirm running count.
6. QA-scan all `batches/` before final application.

### Phase C — Apply the enrichment
7. Run the applier: `python3 stamp_apply.py --vault <source> --out <copy> --blocks-dir ./batches`. Idempotent.
8. Add the CSS snippet for Obsidian rendering.

### Phase D — Stand up the stack
9. Install Ollama; pull the embedder and generator(s):
   ```bash
   ollama pull mxbai-embed-large      # 335M, 669MB — embedder
   ollama pull qwen3:8b                # 8B, ~5GB — local generator
   ```
10. Create Python venv (or conda); `pip install -r requirements.txt`.
11. Configure `.env`:
    ```
    DATA_DIR=/Users/<you>/brain
    CHUNKS_PATH=/Users/<you>/brain/second-brain-rag/chunks.jsonl
    CHROMA_DIR=/Users/<you>/brain/chroma
    COLLECTION=second_brain
    OLLAMA_URL=http://localhost:11434
    EMBED_MODEL=mxbai-embed-large
    GEN_PROVIDER=ollama
    GEN_MODEL=qwen3:8b
    GEMINI_MODEL=gemini-2.5-flash
    GEMINI_API_KEY=<your key, optional>
    TOP_K=6
    MIN_SIMILARITY=0.35
    GRAPH_HOP=true
    ```

### Phase E — Build the index
12. Verify `chunker_v2.py` has `MAX_CHUNK_CHARS=1000` and the force-cut block.
13. `python3 chunker_v2.py` — verify `chunk_tokens_max < ~500`.
14. **Sample-test 5 random chunks against the embedder before the full embed.**
15. `python3 embed_index.py` — watch for <1% failure rate.

### Phase F — Validate
16. `python3 eval_retrieval.py --md report.md` — runs the 21-query benchmark.
17. Acceptance tests via the web UI:
    - Ask a known-covered question → cited answer with dimensions
    - Ask a deliberately absent question → clean refusal
    - Ask a multi-dimensional question → exhaustive synthesis + dimensions panel + gaps list
    - Click "Research these gaps externally" → tagged External Intelligence panel
    - Click "Export PDF" → faithful PDF in browser print dialog

### Phase G — Run
18. `python3 app.py`. Browse to `http://localhost:8000/`.
19. (Optional) wrap in `launchd` (macOS) or `systemd` (Linux) for boot persistence.

---

## 11. Lessons Learned — Fifteen Transferable Insights

These are the lessons that generalize beyond this project. Print and pin.

1. **Generic 500 errors are diagnostic poison.** Always poke the underlying API directly when something fails repeatedly. The real error is often hiding under a generic status code.
2. **Token estimates aren't tokens.** Char-count heuristics underestimate real tokens for technical content. Use the model's actual tokenizer, or set conservative caps and verify on samples.
3. **Embedding models require their specific prefixes.** Each family has its own task-prefix conventions; ignoring them silently degrades retrieval into a mushy band that *looks* normal but isn't.
4. **Refusals are signal, not failure.** A system that refuses cleanly when knowledge is absent is more trustworthy than one that always answers. Refusals map exactly where the knowledge base needs more content.
5. **Measure before optimizing.** The eval harness turned guesses into experiments and made every change measurable. Without it, the embedder swap would have been a wish.
6. **Sample-test before full runs.** Every expensive operation gets a 5-sample pre-flight check. Cycle time for fixing assumptions is the difference between hours and days.
7. **Structure is data engineering.** Uniform note structure isn't pedantry; it's what makes the corpus reliably machine-retrievable.
8. **The human is the persistence layer.** Multi-session work survives tooling resets when the durable artifact lives in human-readable files (JSON batches, Markdown notes).
9. **Idempotency turns mistakes into non-events.** When the same operation can be re-run safely, debugging becomes diagnosis rather than panic.
10. **Synthesis quality is non-negotiable.** Structured panels are *additive*; they must never compress the underlying depth. The user reads the synthesis first; everything else augments it.
11. **External content is always tagged.** Never blend web-sourced findings with local-grounded answers. Provenance is the difference between a tool you can trust and one you can't.
12. **Robust parsing means partial recovery.** When the model misbehaves, salvage what you can rather than give up. Truncated JSON becomes recovered findings; malformed structure becomes labeled prose; mismatched brackets become repaired payloads.
13. **Provider abstraction earns its keep.** When generation quality is your bottleneck, having generation behind one config line means the fix is a deployment change, not a rewrite.
14. **Listen to user pushback, even (especially) when it's profane.** *"Son of a bitch... the cards are not exhaustive"* was the most valuable correction in the project's history. The discipline is hearing the substance under the language.
15. **The journey is the artifact.** Every dead end documented above is more valuable than the final result alone — because it shows how the result was earned.

---

## 12. Obsidian Vault Discipline — The Substrate Under Everything

This section was missing from v1 and v2 of the design book. It's the most important one in this version, because **none of the AI engineering matters if the underlying notes are bad**.

### 12.1 Why hand-authored Obsidian notes?

In an era when AI can generate notes for you, why spend years writing them by hand?

Because **the notes are how you think**. Reading a source and writing a note about it forces synthesis, structure, and the act of putting something into your own words. The note that emerges is no longer the source — it is *your understanding of the source*, integrated with everything else you understand. AI-generated summaries are not your understanding; they are someone else's understanding (the model's, derived from its training data), copied into your vault. The retrieval system can still find them, but they don't compound your expertise.

The vault is also the *substrate of authority*. When the RAG system answers a question, it answers from your notes. If those notes are good, the answers are credible. If they are AI-generated summaries of unread sources, the answers are not credible — they are recycled internet content with your name on top.

**The vault is a personal knowledge asset. Treat it as one.**

### 12.2 How to start a new domain vault

Concrete steps, used for every one of the 15 sub-vaults in My Second Brain:

1. **Pick a domain with a real exam, certification, or syllabus.** Not "AI in general" — pick "NIST AI RMF" or "OSFI E-23" or "BCBS 239." A defined corpus gives you a finite, completable goal. The certification syllabus becomes the natural folder structure.
2. **Create a top-level folder in Obsidian.** Name it after the domain (`AAIR-Vault`, `SWIFT-Vault`, `Open-Banking-RTR-Vault`). This becomes its own sub-vault inside your master vault.
3. **Read one authoritative source end-to-end before authoring any notes.** Not "skim for keywords." Read the OSFI guideline, the BCBS standard, the textbook — cover to cover, with a pen. The reading itself is the foundation; the notes are the artifact.
4. **Identify the natural concept-units.** A 50-page document might decompose into 30 concept-notes (e.g., "Operational Resilience Definition," "Critical Operations," "Tolerances for Disruption," "Third-Party Risk under E-21"). Each concept is one note.
5. **Build a folder structure that mirrors the source's structure**, plus an `_Index.md` or `00-Overview.md` at the top of each subfolder.
6. **Author notes one at a time, in reading order.** Don't bulk-create empty notes — that creates obligation without substance. Build as you read.

### 12.3 The "one concept per note" rule

This is the most important authoring discipline.

- **Wrong:** A note titled `OSFI-E-21-Notes.md` containing 50 paragraphs about everything in the guideline.
- **Right:** Thirty notes, each titled after one concept (`Critical-Operations.md`, `Tolerances-for-Disruption.md`, `Severe-but-Plausible-Scenarios.md`, etc.), each containing the definition, the context, examples, and links to related concepts.

**Why this matters:**
- Retrieval works at the note level. A note about one thing returns clean, targeted hits.
- Wikilinks become meaningful. `[[Tolerances for Disruption]]` is a link to *that concept*, not to a section of a document.
- Re-encountering the concept months later, you read the focused note instead of skimming a long doc.
- The how-layer fits naturally — one Elicit / Specify / Design / D-SIB Hook per *concept*, not one for an entire document.

### 12.4 The wikilink-first habit

Every time a note mentions another concept that has (or should have) its own note, **wikilink it immediately**: `[[Concept Name]]`. Two effects:

1. **You build the graph as you write.** No "I'll add cross-references later" — you never do.
2. **The wikilink reveals missing notes.** A red broken link is a signal: *"this concept deserves its own note, and you haven't written it yet."* The vault tells you what to write next.

Over time the graph becomes the real product. 5,361 wikilink edges across My Second Brain is what makes graph-hop retrieval possible. None of those edges were "added later."

### 12.5 The "one source per session" authoring rhythm

A productive authoring session looks like:

- 90 minutes of reading + note-creation, from one source (one paper, one chapter, one guideline)
- 10–20 notes produced in that session, all on the same domain
- All linked to each other immediately via wikilinks
- Followed by review of yesterday's notes (15 minutes) — refining wording, adding cross-references discovered while writing today's

**What NOT to do:**
- Skip between sources within a session ("a bit of AI risk, then some payments, then back to AI risk"). Loses depth, fragments attention.
- Try to author notes faster than you can read. The reading is the bottleneck, and it should be.
- Outsource the note-authoring to AI. The notes are how you think; outsourcing them outsources your thinking.

### 12.6 The "rewrite when you re-encounter" pattern

Notes are not write-once. When you re-encounter a concept (in another source, in a new project, in a question someone asks), you'll see things you didn't see the first time.

**Discipline:** When you re-encounter the concept, open the existing note and *rewrite the section that's now wrong or shallow*. Don't create a parallel note. Don't leave the original as-is. The note represents your *current* understanding; current understanding changes; the note follows.

After three years of this discipline, the average note in My Second Brain has been rewritten 2-4 times. That accretion is what makes the vault deeper than any single source.

### 12.7 What "manual topicwise learning" means

The reason the RAG system can answer a question about, say, *"the trade-offs between centralized and federated key management under OSFI B-13 expectations"* is that the practitioner has, over time:

- Read OSFI B-13 end-to-end and authored 20 notes on it
- Read three Azure Key Vault architectural references and authored 12 notes
- Read CIBC-internal tokenization patterns (where allowed) and authored 8 notes
- Wikilinked every B-13 expectation to every Key Vault control it engages
- Re-read OSFI B-13 a year later when it was updated, rewrote 6 of the 20 notes

That isn't something AI can do for you. It's the topicwise learning that produces the asset the AI system reads from. **The AI is a tool for accessing a knowledge asset; it does not produce the knowledge asset.**

This is why the design book is named "Second Brain" rather than "AI Assistant." The brain is the vault. The AI is the interface.

---

## 13. Roadmap — The Named Next Stages

These are the concrete next increments. Numbered in priority order.

### Path 1 — Self-Stamping Pipeline
*Effort: medium · Value: high · Risk: low*

Build `bsa_self_stamp.py`. Reads each unstamped note, sends it to Gemini with a tight prompt referencing 3–5 high-quality stamped notes as exemplars, returns valid JSON in the existing batch format. Human reviews/edits each generated block in ~30 seconds rather than authoring from scratch in 5 minutes.

**Why this matters most:** Without it, the system caps out at today's 981 notes. With it, every new BSA engagement, every new regulatory change, every new domain feeds directly into the system. **The multiplier on everything else.**

### Path 2 — Recommended Position
*Effort: low · Value: high (when used surgically) · Risk: medium (hallucination)*

A new `recommended_position` dimension. Returns:
- `choice` — "Choose Security over Agility"
- `rationale` — tied to a specific regulatory anchor or retrieved chunk
- `accepted_cost` — what you're giving up by choosing this
- `conditions_to_flip` — what would change the recommendation
- `confidence` — high / medium / low

Fires only when the question presents a real trade-off. Visual treatment: amber/gold accent, ⚖ glyph, top of the dimensions panel. Low-confidence positions render as "this is genuinely close — see Trade-offs" rather than recommending strongly.

**Hallucination guardrails:** medium-strictness — position only fires when at least one regulatory anchor exists in retrieved content; rationale must cite at least one source.

**Anti-conservative-bias guardrail:** prompt-level instruction — *"If the engineering case for the riskier choice is genuine, name it. Don't default to the conservative answer just because it's defensible."*

This is what moves the system from "tells me the situation" to "tells me what to recommend and why."

### Path 3 — Brief Generator
*Effort: medium-high · Value: very high · Risk: low*

Per-answer button: *"Generate Brief"*. User chooses brief type:
- **Decision memo** (1 page, Director audience, recommendation-forward)
- **Executive talking points** (bulleted, no citations, for going-into-meeting prep)

(Risk briefing, BRD section, stakeholder one-pager, regulatory mapping are v2 once the pattern is validated.)

Fresh Gemini call with brief-specific prompt (different voice, different ordering, executive register) — not a template-fill of the existing synthesis. Citations: executive-style (supporting evidence appendix at end, no inline cite markers in the body for memos; no citations at all for talking points).

External Intelligence content is **excluded from briefs** — provenance must stay clean.

v1: generic templates. v2: house-style learned from 2–3 user-provided sample memos.

**Why this matters:** Briefs are the deliverable that BSA work *produces*. Right now the system gives me analysis; this gives me an artifact I can hand to a Director. Time-to-deliverable drops from hours to minutes.

### Multi-Hop Reasoning
*Effort: high · Value: high for genuinely complex queries · Risk: medium*

The current retrieval surfaces ~6 chunks and the model synthesizes from them. What it can't do well: questions that require chaining facts across vaults. *"How does the Open Banking RTR architecture change my exposure under OSFI E-21 given the CBPR+ migration timeline?"* needs RTR notes + E-21 notes + CBPR+ notes + the connections between them.

Solution: explicit multi-hop.
1. First pass identifies entities/topics in the question
2. Second pass retrieves specifically about each entity
3. Third pass synthesizes the cross-domain answer with explicit provenance: *"this finding came from vault A, that one from vault B, the connection between them is..."*

This is the most ambitious increment. It's also what would distinguish the system from "just RAG" — most RAG systems don't do this.

### Order of execution
**Path 2 → Path 3** first (user's stated preference, decided in v3 brainstorming). Then **Path 1** (self-stamping). Then **Multi-hop** as a research-grade increment when the prior three are mature.

---

## 14. Honest Limitations — What This Doesn't Do

This section is written in **hard register**. The system has real boundaries; pretending otherwise weakens everything else in the document.

### 14.1 What the system still gets wrong

- **Retrieval misses ~19% Top-K.** Across 21 grounded queries, 4 don't surface the expected note even in the top 6 hits. These are usually conceptually-named queries where the model's term doesn't match the corpus's term ("how do I make a payment idempotent" vs notes about "exactly-once semantics"). Hybrid retrieval (BM25 + semantic) would close some but not all of this.

- **The four-field ontology breaks down on purely descriptive concepts.** A note titled "What is a JWT" doesn't really have an Elicit/Specify/Design distinction — those fields end up forced and shallow. Roughly 15% of notes have how-layer blocks that are honestly weaker than the rest of the note. The ontology was designed for *practice* notes, not *reference* notes; the corpus is mixed.

- **Qwen3:8b still produces less breadth than Gemini.** Concise where Gemini is comprehensive. For depth-critical questions, the local default is genuinely worse, not just slower.

- **Gemini still bracket-mismatches occasionally.** The repair handles it, but the underlying model behavior is messy. Future model upgrades may surface new schema errors the repair doesn't anticipate.

- **External Intelligence is a single Gemini call with grounding.** It's not a serious research agent. It doesn't iterate, doesn't re-search when initial results are thin, doesn't synthesize across multiple search passes. It's "Gemini with web search, formatted carefully" — a good tool, not a substitute for actual research.

### 14.2 Where the four-field ontology has real edges

- **Some controls don't have a single regulatory anchor.** A control like "rotate certificates every 90 days" comes from common practice, not from a specific guideline section. Forcing a D-SIB Hook produces vague text like *"OSFI B-13 generally expects cryptographic hygiene."* That's not a citation; it's a paraphrase pretending to be one.

- **Specify and Recommended Controls overlap.** On highly-prescriptive questions, these two dimensions return nearly identical content. They're meant to be different (Specify is what the BSA writes as a requirement; Recommended Controls is what the architect would implement) but the model can't always tell.

- **Open Questions is the noisiest dimension.** The model fills it with generic "how to balance X with Y" rhetorical questions that aren't actually open — they're padding.

### 14.3 What this system is not

- **Not enterprise infrastructure.** A personal system on a personal laptop. No SLA, no HA, no DR.
- **Not authoritative bank guidance.** The how-layer reflects the author's documented practice, not the institution's sanctioned standard.
- **Not a substitute for reading the source.** When a regulatory question really matters, read OSFI E-21, not the RAG output about OSFI E-21.
- **Not a replacement for thinking.** The system can synthesize; it cannot decide. Recommended Position (Path 2) will make this tension sharper, not resolve it.
- **Not a research agent.** External Intelligence is bounded, structured, single-pass.
- **Not unbiased.** Reflects exactly the priors of the practitioner who wrote the notes, including their blind spots.

### 14.4 What would require a fundamentally different architecture

- **Multi-document reasoning across long context.** Current retrieval feeds ~6 chunks; complex regulatory questions sometimes need 30. Beyond a point, this isn't "more chunks" — it's a different system (e.g., hierarchical summarization, agentic retrieval).
- **Reasoning over numerical data.** The vault has plenty of qualitative content, almost no quantitative datasets. Questions like "what's my exposure across the wires book under stress" can't be answered from this corpus regardless of model quality.
- **Truly auditable outputs.** Citations point to notes, not to primary regulatory sources. A real audit trail would require every D-SIB Hook to link to the OSFI publication paragraph it claims to cite. That's a research project, not a tweak.

---

## 15. Final Note — What This Document Is Saying

The artifact is not "an AI assistant over my notes." The artifact is:

> *A measurable, private, regulation-aware reasoning system built on top of a hand-authored execution ontology, with discipline visible at every layer of the stack — and the discipline is the differentiator.*

Every number in this document is measurable. Every architectural claim is verifiable in code. Every dead end is documented honestly. Every transferable lesson is stated explicitly. Every limitation is named in hard register.

The reader who takes one thing from this document should take this:

**This is what it looks like when a single practitioner approaches their own knowledge work as an engineering problem — with measurement at the centre, structure as a data-engineering requirement, faithfulness as a non-negotiable, and the underlying knowledge asset as the long-term commitment — instead of accumulating notes and hoping that's enough.**

The journey from 38% to 67% Top-1 retrieval accuracy is not the achievement. The journey from `qwen2.5:3b` to `qwen3:8b` is not the achievement. The achievement is that **the system is now in honest, measurable, documented use, and the next increments (Path 1, Path 2, Path 3, Multi-hop) are concrete enough to ship.**

The vault is 981 notes today. With Path 1 it grows. With Path 2 it gets a voice. With Path 3 it produces artifacts. With Multi-hop it gains a mind.

But none of those next steps work without the vault. **The brain is the vault. The AI is the interface.**

---

## 16. Appendices

### A. Glossary

- **BSA** — Business Systems Analyst
- **D-SIB** — Domestic Systemically Important Bank
- **How-layer** — the four-field execution block injected into every note (Elicit / Specify / Design / D-SIB Hook)
- **Stamping** — applying the how-layer to a note via `stamp_apply.py`
- **RAG** — Retrieval-Augmented Generation
- **Faithfulness gate / refusal gate** — logic making the assistant decline to answer when no sufficiently-relevant source is retrieved (controlled by `MIN_SIMILARITY` threshold)
- **Idempotent** — an operation safely re-runnable with no duplication or harm
- **Chunk** — a passage of a note prepared for embedding/retrieval
- **Embedding** — a numeric vector representing a chunk's meaning, used for semantic search
- **Top-1 / Top-K** — retrieval accuracy metrics (correct note ranked #1 / anywhere in top K)
- **Provider abstraction** — generation is swappable between local Ollama and hosted Gemini without changing anything else
- **External Intelligence** — web-sourced research, clearly tagged, never blended with local content
- **Dimensions** — the 11+ analytical panels (Elicit, Specify, Design, Operational Risks, etc.) populated when relevant
- **Synthesis** — the primary, exhaustive answer text — never truncated to fit cards
- **Graph-hop** — retrieval enhancement that pulls wikilinked neighbours of the top hits to expand context
- **Partial-JSON recovery** — salvaging complete records from a truncated/malformed JSON response
- **Provenance tag** — the explicit label marking external/web content so it can never be confused for local-grounded synthesis

### B. Regulatory anchors used (reference)

| Anchor | Domain |
|---|---|
| OSFI E-21 | Operational resilience |
| OSFI B-13 | Technology & cyber risk |
| OSFI B-10 | Third-party / outsourcing risk |
| OSFI E-23 | Model risk management (incl. AI/ML) |
| OSFI E-4 / B-7 | Liquidity / FX / settlement |
| OSFI B-15 | Climate / ESG risk |
| BCBS 239 | Risk-data aggregation & reporting |
| BCBS 248 | Intraday liquidity |
| FINTRAC / PCMLTFA | AML / anti-terrorist financing |
| Payments Canada / LYNX / RTR | Canadian payment rails |
| CBPR+ | Cross-border ISO 20022 payments |
| PIPEDA / Quebec Law 25 | Privacy |
| FCAC | Financial consumer conduct |
| CIRO | Investment-industry conduct |
| PCI-DSS | Card data security |
| ISO 27001 / 42001 | Information security / AI management systems |
| EU AI Act | AI regulation (extraterritorial) |

### C. Key configuration values (for tuning)

| Variable | File | Default | Notes |
|---|---|---|---|
| `MAX_CHUNK_CHARS` | `chunker_v2.py` | 1000 | Tightened for mxbai's effective context limit |
| `OVERLAP_CHARS` | `chunker_v2.py` | 200 | Ensures cross-chunk continuity |
| `MIN_SIMILARITY` | `.env` | 0.35 | Refusal gate threshold (raise to be stricter) |
| `TOP_K` | `.env` | 6 | Candidate count returned to generator |
| `GRAPH_HOP` | `.env` | true | Pull wikilinked neighbors for context |
| `EMBED_MODEL` | `.env` | mxbai-embed-large | Swap to bge-m3 if scaling beyond ~50K chunks |
| `GEN_PROVIDER` | `.env` | ollama | Default; per-query toggle overrides |
| `GEN_MODEL` | `.env` | qwen3:8b | Local generation model |
| `GEMINI_MODEL` | `.env` | gemini-2.5-flash | Hosted generation + external research |
| `MAX_SOURCES_PER_FINDING` | `research.py` | 5 | External research source cap |
| `maxOutputTokens` (gen) | `generate.py` | 4096 | Per-call ceiling for synthesis |
| `maxOutputTokens` (research) | `research.py` | 8192 | Doubled to fit 6+ gap queries |
| `thinkingBudget` | both | 0 | Disables Gemini's hidden reasoning tokens |

### D. Worked examples — illustrative query/response patterns

**Example 1 — Faithfulness gate firing cleanly**

> Query: *"What is the difference between mTLS, TLS, and SSL?"*
> Response: Synthesis correctly describes TLS (one-way) and mTLS (mutual), pulling real context from SWIFT Alliance Gateway and Open Banking notes. SSL section: gap explicitly listed — *"the notes do not define SSL as distinct from TLS."*
> **Why this matters:** Demonstrates the faithfulness gate doing its job — refusing to invent content rather than fabricating. This is the property regulated environments require.

**Example 2 — Multi-dimensional analysis with regulatory anchors**

> Query: *"We are introducing AI-driven fraud scoring into RTR payments. What operational, regulatory, resilience, and governance concerns emerge?"*
> Response: Exhaustive synthesis (multi-paragraph). 11 dimensions populated. Extra dimension `latency_budget` added by the model. Regulatory anchors lifted: OSFI E-23, FINTRAC, FCAC. Six gaps named specifically. Confidence: high.
> **Why this matters:** Demonstrates the system at full depth — covering ops, reg, resilience, governance simultaneously, with concrete Canadian D-SIB framing throughout.

**Example 3 — External Intelligence used surgically**

> Query: *"How to write a quality NFR for an enterprise payment system?"*
> Response: Local synthesis pulls from CBAP, SWIFT, and Card-Payments vaults. Six gaps named. User clicks "Research these gaps externally."
> External Intelligence panel returns 6 findings, each with up to 5 real source URLs (OSFI, McCarthy Tétrault, Torys, arXiv, etc.), confidence per finding, caveats. Visually distinct teal panel. Provenance tag visible.
> **Why this matters:** Demonstrates the two-track architecture — local-grounded synthesis is primary, web-sourced research is explicit opt-in, clearly tagged, never blended.

### E. Quick command reference

```bash
# Stamp a fresh batch into a vault copy
python3 stamp_apply.py --vault <source> --out <copy> --blocks-dir ./batches

# Chunk (after stamping or after notes change)
python3 chunker_v2.py

# Embed (after chunking)
caffeinate -i python3 embed_index.py     # caffeinate keeps macOS awake

# Evaluate
python3 eval_retrieval.py --md retrieval-eval-report.md

# Run the server
python3 app.py     # listens on 0.0.0.0:8000

# Direct retrieval debug
python3 retrieval.py "your question here"

# Direct generation debug
python3 generate.py "your question here"

# Direct external research debug
python3 research.py "your question" "gap one" "gap two"
```

---

*End of document. All numbers measurable; all code in the repository; eval harness rerunnable on demand; partial-recovery handles the messy cases honestly; limitations named in hard register; the next increments are concrete.*

*The brain is the vault. The AI is the interface. The journey is the artifact.*
