#!/usr/bin/env python3
"""
app.py — FastAPI server: /health, /vaults, /query, /research_gaps, UI at /.

Endpoints:
  GET  /health  -> {"ok","gen_provider","gen_model","indexed_chunks"}
  GET  /vaults  -> {"vaults":[...]}
  POST /query   -> {answer, refused, citations, best_similarity, provider, structured}
  POST /research_gaps -> External Intelligence findings (B3 explicit mode)

Run:  python3 app.py
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import chromadb
from backend import config
from retrieval import retrieve
from generate import answer as gen_answer
from research import research_gaps

app = FastAPI(title="Second Brain")

UI_DIR = Path(__file__).parent / "ui"


class Query(BaseModel):
    query: str
    vault: str | None = None
    provider: str | None = None    # "ollama" | "gemini" — overrides .env for this query only


class ResearchRequest(BaseModel):
    query: str
    gaps: list[str]


@app.get("/health")
def health():
    ok = True
    try:
        chroma = chromadb.PersistentClient(path=config.CHROMA_DIR)
        n = chroma.get_collection(config.COLLECTION).count()
    except Exception:
        ok, n = False, 0
    return {
        "ok": ok,
        "gen_provider": config.GEN_PROVIDER,
        "gen_model": (config.GEN_MODEL if config.GEN_PROVIDER == "ollama"
                      else config.GEMINI_MODEL),
        "indexed_chunks": n,
        "research_available": bool(config.GEMINI_API_KEY),
    }


@app.get("/vaults")
def vaults():
    try:
        chroma = chromadb.PersistentClient(path=config.CHROMA_DIR)
        col = chroma.get_collection(config.COLLECTION)
        got = col.get(include=["metadatas"], limit=20000)
        vs = sorted({m.get("vault") for m in got["metadatas"] if m.get("vault")})
        return {"vaults": vs}
    except Exception:
        return {"vaults": []}


@app.post("/query")
def query(q: Query):
    # Per-query provider override (UI toggle). Temporarily swap config, restore in finally.
    original_provider = config.GEN_PROVIDER
    if q.provider in ("ollama", "gemini"):
        config.GEN_PROVIDER = q.provider
    try:
        result = gen_answer(q.query, vault=q.vault)
        provider_tag = "local" if config.GEN_PROVIDER == "ollama" else "cloud"
    finally:
        config.GEN_PROVIDER = original_provider

    if result["refused"]:
        return JSONResponse({
            "answer": result["answer"],
            "refused": True,
            "citations": [],
            "best_similarity": result["top_similarity"],
            "provider": provider_tag,
            "structured": None,
        })

    r = retrieve(q.query, vault=q.vault)
    citations, seen = [], set()
    n = 1
    for h in r["hits"]:
        m = h["metadata"]
        key = m.get("note_path")
        if not key or key in seen:
            continue
        seen.add(key)
        citations.append({
            "n": n,
            "note_title": m.get("note_title", ""),
            "vault": m.get("vault", ""),
            "section": m.get("section", ""),
        })
        n += 1

    return JSONResponse({
        "answer": result["answer"],
        "refused": False,
        "citations": citations,
        "best_similarity": result["top_similarity"],
        "provider": provider_tag,
        "structured": result.get("structured"),
    })


@app.post("/research_gaps")
def research_gaps_endpoint(req: ResearchRequest):
    """B3 explicit external-research mode. Always returns clearly-tagged
    External Intelligence — never blended with local synthesis."""
    return JSONResponse(research_gaps(req.query, req.gaps))


@app.get("/")
def root():
    return FileResponse(str(UI_DIR / "index.html"))


if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR)), name="ui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
