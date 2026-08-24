"""
config.py — single source of truth + provider abstraction.

Generation can be swapped between local Ollama and Gemini's free tier
WITHOUT touching retrieval, indexing, or the UI. Set GEN_PROVIDER in .env.
Embeddings stay local (Ollama) always — they're free, fast, and private.
"""
import os
from dotenv import load_dotenv
load_dotenv()

# ---- paths (point DATA_DIR at the external 1.5TB SSD on the Mac Pro) ----
DATA_DIR        = os.getenv("DATA_DIR", "/data/brain")
CHUNKS_PATH     = os.getenv("CHUNKS_PATH", os.path.join(DATA_DIR, "chunks.jsonl"))
CHROMA_DIR      = os.getenv("CHROMA_DIR", os.path.join(DATA_DIR, "chroma"))
COLLECTION      = os.getenv("COLLECTION", "second_brain")

# ---- embeddings (always local Ollama) ----
OLLAMA_URL      = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL     = os.getenv("EMBED_MODEL", "nomic-embed-text")

# ---- generation provider: "ollama" (local) | "gemini" (free cloud) ----
GEN_PROVIDER    = os.getenv("GEN_PROVIDER", "ollama")
GEN_MODEL       = os.getenv("GEN_MODEL", "qwen2.5:7b")          # ollama
GEMINI_MODEL    = os.getenv("GEMINI_MODEL", "gemini-2.0-flash") # gemini
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY", "")

# ---- retrieval tuning ----
TOP_K           = int(os.getenv("TOP_K", "6"))
MIN_SIMILARITY  = float(os.getenv("MIN_SIMILARITY", "0.35"))  # refusal gate (semantic)
GRAPH_HOP       = os.getenv("GRAPH_HOP", "true").lower() == "true"

# ---- hybrid retrieval (Phase 3a — BM25 + semantic via RRF) ----
HYBRID_ENABLED     = os.getenv("HYBRID_ENABLED", "true").lower() == "true"
RRF_K              = int(os.getenv("RRF_K", "60"))            # RRF damping constant
HYBRID_CANDIDATES  = int(os.getenv("HYBRID_CANDIDATES", "20"))# per-retriever pool
HOW_BOOST          = float(os.getenv("HOW_BOOST", "0.08"))    # know-vs-do nudge

# ---- reranker (Phase 3c) — OFF: measured worse than 3a on the 21-q eval ----
RERANK_ENABLED  = os.getenv("RERANK_ENABLED", "false").lower() == "true"
RERANK_POOL     = int(os.getenv("RERANK_POOL", "20"))
RERANK_MODEL    = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-base")
RERANK_DEVICE   = os.getenv("RERANK_DEVICE") or None          # None -> auto (mps/cpu)
RERANK_MAXLEN   = int(os.getenv("RERANK_MAXLEN", "512"))