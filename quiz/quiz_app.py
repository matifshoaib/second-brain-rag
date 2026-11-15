#!/usr/bin/env python3
"""
quiz_app.py - Second Brain Drill server (port 8010).

Runs alongside app.py and reads the same chunks.jsonl. It never touches the
RAG index or the main app. Your answers and schedule live in quiz/quiz.db.

Run:   cd ~/brain/second-brain-rag && python3 quiz/quiz_app.py
Open:  http://localhost:8010
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE.parent))

from fastapi import FastAPI, HTTPException                   # noqa: E402
from fastapi.responses import FileResponse, JSONResponse     # noqa: E402
from pydantic import BaseModel                               # noqa: E402

from backend import config                                   # noqa: E402
from engine import Drill, LLMError, Ollama                   # noqa: E402

DB_PATH = os.getenv("QUIZ_DB", str(HERE / "quiz.db"))
MODEL = os.getenv("QUIZ_MODEL", config.GEN_MODEL)
PORT = int(os.getenv("QUIZ_PORT", "8010"))
PREFETCH = int(os.getenv("QUIZ_PREFETCH", "2"))

llm = Ollama(config.OLLAMA_URL, MODEL)
drill = Drill(DB_PATH, config.CHUNKS_PATH, llm)
app = FastAPI(title="Second Brain Drill")


# ---------------------------------------------------------------------------
# Prefetch: keep the next couple of questions generated in the background so
# the next card appears instantly instead of after a 20-40s model call.
# ---------------------------------------------------------------------------
_pf_lock = threading.Lock()
_pf_running = False
_pf_error = {"msg": None, "at": 0.0}
_grading = threading.Event()   # a user is waiting on a grade: prefetch steps aside


def prefetch(vault: str | None, extra: bool, exclude: set[str]) -> None:
    global _pf_running
    with _pf_lock:
        if _pf_running:
            return
        _pf_running = True

    def run():
        global _pf_running
        try:
            for p in drill.upcoming(vault, extra, n=PREFETCH, exclude=exclude):
                if _grading.is_set():
                    break
                if not drill.pending_question(p):
                    drill.ensure_question(p)
            _pf_error["msg"] = None
        except LLMError as e:
            _pf_error.update(msg=str(e), at=time.time())
        except Exception as e:  # never let prefetch take the server down
            _pf_error.update(msg=f"prefetch failed: {e}", at=time.time())
        finally:
            with _pf_lock:
                _pf_running = False

    threading.Thread(target=run, daemon=True).start()


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
class Answer(BaseModel):
    question_id: int
    answer: str = ""
    idk: bool = False
    vault: str | None = None
    extra: bool = False


class Override(BaseModel):
    review_id: int
    verdict: str


class Skip(BaseModel):
    question_id: int
    bad: bool = False
    vault: str | None = None
    extra: bool = False


class Settings(BaseModel):
    new_per_day: int


@app.get("/")
def root():
    return FileResponse(str(HERE / "ui" / "drill.html"))


@app.get("/api/state")
def state(vault: str | None = None):
    return {
        "stats": drill.stats(vault or None),
        "vaults": sorted({n.vault for n in drill.notes.values()}),
        "model": MODEL,
        "ollama": llm.ping(),
        "prefetch_error": _pf_error["msg"],
    }


@app.get("/api/next")
def next_card(vault: str | None = None, extra: bool = False, after: str | None = None):
    vault = vault or None
    exclude = {after} if after else set()
    paths = drill.upcoming(vault, extra, n=1, exclude=exclude)
    if not paths and after:   # the only card left is the one just answered
        paths = drill.upcoming(vault, extra, n=1)
    if not paths:
        return {"done": True, "stats": drill.stats(vault)}
    p = paths[0]
    try:
        q = drill.ensure_question(p)
    except LLMError as e:
        raise HTTPException(503, str(e))
    prefetch(vault, extra, exclude={p})
    return {"done": False, "card": drill.card_view(p, q), "stats": drill.stats(vault)}


@app.post("/api/answer")
def answer(a: Answer):
    _grading.set()
    try:
        res = drill.grade(a.question_id, a.answer, a.idk)
    except KeyError:
        raise HTTPException(404, "Question not found")
    except LLMError as e:
        raise HTTPException(503, str(e))
    finally:
        _grading.clear()
    prefetch(a.vault or None, a.extra, exclude=set())
    return JSONResponse(res)


@app.post("/api/override")
def override(o: Override):
    try:
        return drill.override(o.review_id, o.verdict)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.post("/api/skip")
def skip(s: Skip):
    drill.skip(s.question_id, s.bad)
    return {"ok": True}


@app.post("/api/settings")
def settings(s: Settings):
    drill.set_setting("new_per_day", max(0, min(200, s.new_per_day)))
    return drill.stats()


@app.post("/api/reload")
def reload_corpus():
    return drill.reload()


if __name__ == "__main__":
    import uvicorn
    print(f"[drill] {len(drill.notes)} drillable notes · model {MODEL} · db {DB_PATH}")
    print(f"[drill] open http://localhost:{PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
