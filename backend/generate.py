"""
generate.py — citation-grounded generation with faithfulness enforced.

Faithfulness controls (not assumed):
  1. Refusal gate: empty/weak retrieval -> we don't call the model at all.
  2. Hard system prompt: answer ONLY from context; cite [n]; admit gaps.
  3. Context is numbered so the model can cite, and we return the mapping
     so the UI can render source cards.
Provider-swappable: Ollama (local) or Gemini (free tier) per config.
"""
import httpx, config as C

SYSTEM = """You are the user's second brain. Answer ONLY using the numbered \
context below, which is drawn from the user's own notes. Rules:
- Use only facts present in the context. Do NOT add outside knowledge.
- Cite the source of each claim inline as [n], matching the context number.
- If the context does not contain the answer, say exactly: \
"That isn't in my notes yet." Do not guess.
- Be concise and direct. Write the way a senior BSA/architect briefs a peer.
- When the notes include a "How a BSA Uses This" angle, lead with the practical \
move, then the design implication, then the Canadian/D-SIB regulatory hook."""

REFUSAL = "That isn't in my notes yet."

def _context(chunks):
    blocks = []
    for i, c in enumerate(chunks, 1):
        blocks.append(f"[{i}] ({c['note_title']} \u00b7 {c['vault']} \u00b7 \u00a7{c['section']})\n{c['text']}")
    return "\n\n".join(blocks)

def _ollama(prompt):
    r = httpx.post(f"{C.OLLAMA_URL}/api/generate",
        json={"model": C.GEN_MODEL, "prompt": prompt, "system": SYSTEM,
              "stream": False, "options": {"temperature": 0.2}}, timeout=300)
    r.raise_for_status()
    return r.json()["response"].strip()

def _gemini(prompt):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{C.GEMINI_MODEL}:generateContent?key={C.GEMINI_API_KEY}")
    r = httpx.post(url, json={
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2}}, timeout=120)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

def answer(query, retrieval):
    if retrieval["refuse"]:
        return {"answer": REFUSAL, "refused": True, "citations": [],
                "best_similarity": retrieval["best_similarity"]}

    chunks = retrieval["chunks"]
    prompt = f"CONTEXT:\n{_context(chunks)}\n\nQUESTION: {query}\n\nAnswer (cite [n]):"
    text = _ollama(prompt) if C.GEN_PROVIDER == "ollama" else _gemini(prompt)

    citations = [{
        "n": i, "note_title": c["note_title"], "vault": c["vault"],
        "section": c["section"], "note_path": c["note_path"],
        "similarity": c["similarity"],
    } for i, c in enumerate(chunks, 1)]

    return {"answer": text, "refused": False, "citations": citations,
            "best_similarity": retrieval["best_similarity"],
            "provider": C.GEN_PROVIDER}
