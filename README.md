# Second Brain — local RAG over your Obsidian vault

A private, $0, retrieval-grounded assistant over all 981 of your notes.
Runs entirely on your Mac Pro (Proxmox). Web UI, citation-grounded answers,
refuses when something isn't in your notes.

```
Obsidian vault ─▶ chunker.py ─▶ chunks.jsonl ─▶ embed_index.py ─▶ ChromaDB
                                                                      │
  Browser ◀── UI (Product Clean) ◀── FastAPI /query ◀── retrieval + generation
```

- **Embeddings**: `nomic-embed-text` (local Ollama) — free, private
- **Generation**: `qwen2.5:7b` (local Ollama) — swap to Gemini free tier via `.env`
- **Vector store**: ChromaDB (local, on the 1.5TB external SSD)
- **Backend**: FastAPI · **UI**: single-page, served by the backend

---

## 0. Hardware reality (your box)
Mac Pro 2013, 128GB RAM, dual FirePro GPUs. The GPUs can't accelerate modern
LLMs and you're on Proxmox/Linux (no Metal), so **generation is CPU-only**.
A 7B Q4 model streams at reading pace — fine for a personal brain. If it drags,
drop to `qwen2.5:3b`, or set `GEN_PROVIDER=gemini` (free tier) — embeddings and
everything else stay local.

## 1. Create the LXC container (on Proxmox)
- Ubuntu 22.04 LXC, **8 vCPU, 32GB RAM**, 40GB root disk
- **Mount the external 1.5TB SSD** into the container at `/data` (model weights +
  index live here, not on the 256GB internal disk)

## 2. Install Ollama + pull models
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull nomic-embed-text      # ~275MB, embeddings
ollama pull qwen2.5:7b            # ~4.7GB, generation  (or qwen2.5:3b if slow)
```

## 3. Install the app
```bash
apt update && apt install -y python3-pip
git clone <this-project> /opt/brain   # or copy the folder
cd /opt/brain
pip install -r requirements.txt
cp .env.example .env                  # edit if your paths differ
mkdir -p /data/brain
```

## 4. Build the index (one time, ~minutes)
```bash
# (a) chunk your vault -> chunks.jsonl
#     edit CORPUS path at the top of chunker.py to your vault location
python chunker.py
cp chunks.jsonl /data/brain/

# (b) embed + load into ChromaDB
cd backend
python embed_index.py
```

## 5. Run it
```bash
cd backend
uvicorn app:app --host 0.0.0.0 --port 8080
```
Open `http://<container-ip>:8080` in your browser. Ask your brain.

---

## Re-indexing when notes change
Re-run steps 4(a) and 4(b). `embed_index.py` upserts by `chunk_id`, so changed
notes update in place — no full rebuild needed.

## Faithfulness — how it's enforced (not assumed)
1. **Refusal gate** — if the best retrieved chunk is below `MIN_SIMILARITY`,
   the model is never called; the UI shows "That isn't in my notes yet."
2. **Hard grounding prompt** — answer only from numbered context; cite `[n]`.
3. **Citations returned** — every answer renders source cards (note · vault · §section)
   so you can verify against the original note in one click.

## Swapping generation to the free cloud tier
```
# in .env
GEN_PROVIDER=gemini
GEMINI_API_KEY=<your free key from aistudio.google.com>
```
Embeddings, vector store, retrieval, and UI are unchanged.

## Project layout
```
brain_rag/
├── chunker.py            # vault -> chunks.jsonl (structure-aware)
├── requirements.txt
├── .env.example
├── backend/
│   ├── config.py         # paths + provider abstraction
│   ├── embed_index.py    # chunks -> ChromaDB (Ollama embeddings)
│   ├── retrieval.py      # semantic + metadata filter + graph-hop + refusal gate
│   ├── generate.py       # citation-grounded generation, faithfulness enforced
│   └── app.py            # FastAPI: /query /vaults /health + serves UI
└── ui/
    └── index.html        # Product-Clean single-page app
```

## Roadmap (next increments)
- The "how-layer" corpus pass (`[!bsa-how]` callouts + frontmatter) — turns this
  from a *know* assistant into a *do* assistant and adds metadata for sharper filters
- Streaming responses (token-by-token) once on the box
- Optional Ragas eval harness as a CI gate on retrieval quality
