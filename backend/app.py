"""
app.py — the backend both the web UI (and any future client) call.

Endpoints:
  GET  /           -> serves the Product-Clean UI
  GET  /health     -> liveness + config snapshot
  GET  /vaults     -> list of vaults for the filter dropdown
  POST /query      -> {query, vault?} -> grounded answer + citations
Run: uvicorn app:app --host 0.0.0.0 --port 8080
"""
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os, config as C
import retrieval, generate

app = FastAPI(title="Second Brain")
UI = os.path.join(os.path.dirname(__file__), "..", "ui", "index.html")

class Q(BaseModel):
    query: str
    vault: str | None = None

@app.get("/")
def home():
    return FileResponse(UI)

@app.get("/health")
def health():
    return {"ok": True, "gen_provider": C.GEN_PROVIDER,
            "gen_model": C.GEN_MODEL if C.GEN_PROVIDER == "ollama" else C.GEMINI_MODEL,
            "embed_model": C.EMBED_MODEL, "graph_hop": C.GRAPH_HOP}

@app.get("/vaults")
def vaults():
    # distinct vaults from the collection metadata
    got = retrieval._col.get(include=["metadatas"], limit=20000)
    vs = sorted({m["vault"] for m in got["metadatas"]}) if got["metadatas"] else []
    return {"vaults": vs}

@app.post("/query")
def query(q: Q):
    r = retrieval.retrieve(q.query, vault=q.vault)
    return generate.answer(q.query, r)
