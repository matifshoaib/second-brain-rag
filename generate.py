#!/usr/bin/env python3
"""
generate.py — exhaustive, grounded, cited answer + structured analytical dimensions.

Response shape returned to the UI:
    {
      "synthesis":  "<LONG, exhaustive answer — the primary content>",
      "dimensions": {
          # Populated only when relevant. ARRAYS of strings (forced via the prompt).
          # 11 default keys + any domain-specific extras the model adds (e.g. latency_budget).
          "elicit":               ["item 1", "item 2", ...],
          "specify":              [...],
          "design":               [...],
          "operational_risks":    [...],
          "regulatory_concerns":  [...],
          "trade_offs":           [...],
          "failure_scenarios":    [...],
          "governance_gaps":      [...],
          "recommended_controls": [...],
          "escalation_triggers":  [...],
          "open_questions":       [...]
      },
      "regulatory_anchors": ["OSFI E-21", ...],
      "gaps":               [...],
      "confidence":         "high" | "medium" | "low"
    }

Hardening in this version:
  - SYSTEM_PROMPT explicitly demands ARRAYS for every dimension (fixes Qwen3
    sometimes collapsing arrays into comma-separated prose strings).
  - JSON repair pass handles Gemini's occasional bracket-mismatch errors.
  - `_normalize_structured` preserves array shape so the UI renders bullets.
  - Gemini thinkingBudget=0 + maxOutputTokens=4096 keep daily quota healthy.
  - Ollama num_ctx=8192 / num_predict=4096 give room for exhaustive answers.
  - Provider-swappable: GEN_PROVIDER = "ollama" | "gemini".
"""
import json
import re

import httpx

from backend import config
from retrieval import retrieve

REFUSAL_TEXT = ("That isn't in my notes yet. I can only answer from the "
                "Second Brain, and nothing sufficiently relevant came back "
                "for this question.")

SYSTEM_PROMPT = """You are a deep retrieval assistant over Muhammad Atif's "Second Brain" — a curated \
knowledge base for a senior Business Systems Analyst and Enterprise Architect at a Canadian D-SIB. \
You serve BOTH workflow needs (BSA elicitation/specification/design) AND learning needs \
(teaching-grade explanations of any topic in the corpus).

Return ONE JSON object with this schema — no markdown, no code fences, no commentary outside the JSON:

{
  "synthesis": "<the primary answer. LONG. EXHAUSTIVE. Write as deeply as the question warrants. \
DO NOT compress, truncate, or summarize to fit card-shaped panels. Use the full available context. \
If the question is broad (e.g. 'what are mandatory controls for X' or 'what concerns emerge from Y'), \
produce a teaching-grade treatment — multi-paragraph, with sub-structure when useful, naming specific \
controls, standards, mechanisms, and trade-offs from the notes. This is the answer the user reads first.>",

  "dimensions": {
    "elicit":               ["<question 1>", "<question 2>", "..."],
    "specify":              ["<requirement 1>", "<requirement 2>", "..."],
    "design":               ["<decision 1>", "<decision 2>", "..."],
    "operational_risks":    ["<risk 1>", "<risk 2>", "..."],
    "regulatory_concerns":  ["<concern 1>", "<concern 2>", "..."],
    "trade_offs":           ["<trade-off 1>", "<trade-off 2>", "..."],
    "failure_scenarios":    ["<scenario 1>", "<scenario 2>", "..."],
    "governance_gaps":      ["<gap 1>", "<gap 2>", "..."],
    "recommended_controls": ["<control 1>", "<control 2>", "..."],
    "escalation_triggers":  ["<trigger 1>", "<trigger 2>", "..."],
    "open_questions":       ["<question 1>", "<question 2>", "..."]
  },

  "regulatory_anchors": ["<each as its own string, e.g. \\"OSFI E-21\\", \\"BCBS 239\\", \\"PCI-DSS Req 7\\">"],
  "gaps":               ["<aspects the notes do NOT cover — be honest, specific>"],
  "confidence":         "high" | "medium" | "low"
}

CRITICAL SHAPE RULES (do not deviate):
- EVERY dimension field MUST be a JSON array of strings. NEVER a single string. NEVER a comma-separated paragraph. NEVER a sentence joining multiple items with "and".
- WRONG:  "specify": "MFA for all users, PIM for privileged access, Private Endpoints for data"
- RIGHT:  "specify": ["MFA for all users via Entra ID Conditional Access", "PIM for privileged access", "Private Endpoints for all data services"]
- Each array item is ONE atomic insight — a single question, a single requirement, a single risk. Do NOT cram multiple items into one string.
- If a dimension has only one item, still use an array: ["only item"].
- If a dimension is not applicable to the question, OMIT THE KEY ENTIRELY rather than padding with generic filler.
- You MAY add additional dimension keys beyond the fixed list above when the domain warrants (e.g. "latency_budget" for payments-architecture, "bias_surface" for AI risk). Use snake_case keys, same array-of-strings shape.

Content rules:
- The "synthesis" field is mandatory and must be EXHAUSTIVE. Do not truncate to make cards look balanced. The cards are SECONDARY — they augment the synthesis, never replace it.
- Use ONLY the CONTEXT below. Do not invent facts, regulations, or definitions. If something is not in the notes, list it under "gaps".
- Regulatory anchors must be lifted from the notes (D-SIB Hook / bsa_dsib content).
- "confidence" reflects how directly the notes answer: "high" = explicit, "medium" = synthesis required, "low" = partial.
- Return the JSON object only. No prose before or after."""


def _build_context(hits: list) -> str:
    blocks = []
    for h in hits:
        m = h["metadata"]
        tag = "[HOW-LAYER] " if m.get("chunk_type") == "how_layer" else ""
        src = m.get("note_path", "unknown")
        blocks.append(f"--- {tag}Source: {src} ---\n{h['text']}")
    return "\n\n".join(blocks)


def _sources(hits: list) -> list:
    seen, out = set(), []
    for h in hits:
        p = h["metadata"].get("note_path")
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _gen_ollama(prompt: str, client: httpx.Client) -> str:
    r = client.post(
        f"{config.OLLAMA_URL}/api/generate",
        json={
            "model": config.GEN_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",   # Ollama-native JSON mode — keeps Qwen3 on schema
            "options": {
                "num_ctx": 8192,
                "num_predict": 4096,
                "temperature": 0.3,
            },
        },
        timeout=300.0,
    )
    r.raise_for_status()
    return r.json()["response"].strip()


def _gen_gemini(prompt: str, client: httpx.Client) -> str:
    if not config.GEMINI_API_KEY:
        return ('{"synthesis":"[generation error] GEN_PROVIDER=gemini but '
                'GEMINI_API_KEY is empty. Set it in .env or switch '
                'GEN_PROVIDER=ollama.","dimensions":{},'
                '"regulatory_anchors":[],"gaps":[],"confidence":"low"}')
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 4096,
            "temperature": 0.3,
            # 2.5-flash: disable internal "thinking" tokens (would burn daily quota fast)
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    r = client.post(url, json=body, timeout=180.0)
    r.raise_for_status()
    data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _try_repair_json(s: str) -> str:
    """Repair common JSON errors the model emits (mismatched brackets, trailing commas)."""
    if not s:
        return s
    # 1. trailing commas before ] or }
    s = re.sub(r",(\s*[\]}])", r"\1", s)
    # 2. depth-track and swap mismatched closers; close any open tail
    out = []
    stack = []
    in_string = False
    escape = False
    for c in s:
        if escape:
            out.append(c); escape = False; continue
        if c == "\\":
            out.append(c); escape = True; continue
        if c == '"':
            in_string = not in_string; out.append(c); continue
        if in_string:
            out.append(c); continue
        if c == "{":
            stack.append("}"); out.append(c)
        elif c == "[":
            stack.append("]"); out.append(c)
        elif c in "}]":
            if stack and stack[-1] != c:
                expected = stack.pop(); out.append(expected)
            elif stack:
                stack.pop(); out.append(c)
        else:
            out.append(c)
    repaired = "".join(out)
    while stack:
        repaired += stack.pop()
    return repaired


def _extract_json(raw: str):
    """Robust JSON extraction: strip fences, try clean parse, try repaired parse, give up."""
    if not raw:
        return None
    s = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", s, re.DOTALL)
    if fence:
        s = fence.group(1).strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    try:
        return json.loads(_try_repair_json(s))
    except Exception:
        pass
    # last resort: brace-match a candidate and try repair on it
    start = s.find("{")
    if start == -1:
        return None
    depth, in_string, escape, end = 0, False, False, -1
    for i in range(start, len(s)):
        c = s[i]
        if escape:
            escape = False; continue
        if c == "\\":
            escape = True; continue
        if c == '"':
            in_string = not in_string; continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i; break
    candidate = s[start:end + 1] if end != -1 else s[start:]
    try:
        return json.loads(_try_repair_json(candidate))
    except Exception:
        return None


def _split_into_items(text: str) -> list[str]:
    """When the model returns a single string where an array was expected,
    try to split it into reasonable items. Used by the normalizer as a safety net
    in addition to the UI's defensive splitter."""
    if not text:
        return []
    # First try splitting on sentence boundaries (period + space + capital letter)
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z(])', text.strip())
    sentences = [s.strip().rstrip('.') for s in sentences if s.strip()]
    if len(sentences) >= 3:
        return sentences
    # Otherwise try comma split if 3+ commas suggest a list
    if text.count(',') >= 3:
        parts = [p.strip().rstrip('.') for p in text.split(',') if p.strip()]
        if len(parts) >= 3:
            return parts
    # Fallback: return as single-item list
    return [text.strip()]


def _normalize_structured(d: dict) -> dict:
    """Coerce to schema. PRESERVES arrays so the UI renders bullets.
    Strings stay strings (UI will defensively split if they look list-like)."""
    def s(v):
        return str(v).strip() if v is not None else ""
    def lst(v):
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str) and v.strip():
            return [v.strip()]
        return []

    raw_dims = d.get("dimensions", {}) or {}
    if not isinstance(raw_dims, dict):
        raw_dims = {}
    dimensions = {}
    for k, v in raw_dims.items():
        if isinstance(v, list):
            items = [str(x).strip() for x in v if x is not None and str(x).strip()]
            if items:
                dimensions[str(k)] = items
        else:
            text = s(v)
            if text:
                # If the string looks like a list (multiple sentences or many commas),
                # split it server-side as a safety net. UI also handles this.
                items = _split_into_items(text)
                dimensions[str(k)] = items if len(items) > 1 else text

    conf = s(d.get("confidence", "")).lower()
    if conf not in {"high", "medium", "low"}:
        conf = "medium"

    return {
        "synthesis":          s(d.get("synthesis", "")),
        "dimensions":         dimensions,
        "regulatory_anchors": lst(d.get("regulatory_anchors", [])),
        "gaps":               lst(d.get("gaps", [])),
        "confidence":         conf,
    }


def answer(query: str, vault: str | None = None) -> dict:
    r = retrieve(query, vault=vault)

    if r["refused"]:
        return {
            "answer": REFUSAL_TEXT,
            "refused": True,
            "structured": None,
            "sources": [],
            "how_mode": r["how_mode"],
            "top_similarity": r["top_similarity"],
        }

    context = _build_context(r["hits"])
    prompt = (f"{SYSTEM_PROMPT}\n\n=== CONTEXT (the only knowledge you may use) ==="
              f"\n{context}\n\n=== QUESTION ===\n{query}\n\n=== JSON RESPONSE ===\n")

    raw = ""
    with httpx.Client() as client:
        try:
            if config.GEN_PROVIDER == "gemini":
                raw = _gen_gemini(prompt, client)
            else:
                raw = _gen_ollama(prompt, client)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raw = ('{"synthesis":"Rate limit hit (Gemini free tier: ~15 req/min). '
                       'Please wait 60 seconds and try again.","dimensions":{},'
                       '"regulatory_anchors":[],"gaps":[],"confidence":"low"}')
            else:
                raw = json.dumps({
                    "synthesis": f"[generation error] {e}",
                    "dimensions": {}, "regulatory_anchors": [],
                    "gaps": [], "confidence": "low",
                })
        except Exception as e:
            raw = json.dumps({
                "synthesis": f"[generation error] {e}",
                "dimensions": {}, "regulatory_anchors": [],
                "gaps": [], "confidence": "low",
            })

    parsed = _extract_json(raw)
    if parsed is not None:
        structured = _normalize_structured(parsed)
        answer_text = structured["synthesis"] or "[Model returned structured output without a synthesis field.]"
    else:
        structured = None
        answer_text = raw or "[Model returned an empty response.]"

    return {
        "answer": answer_text,
        "refused": False,
        "structured": structured,
        "sources": _sources(r["hits"]),
        "how_mode": r["how_mode"],
        "top_similarity": r["top_similarity"],
    }


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "how do I handle idempotency in wire payments?"
    out = answer(q)
    print(json.dumps(out, indent=2))
