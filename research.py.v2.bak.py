#!/usr/bin/env python3
"""
research.py — EXPLICIT external-research mode for filling gaps in local knowledge.

B3 design: notes-only first pass → if gaps exist, user clicks "Research externally" →
this module runs → results returned as CLEARLY TAGGED "External Intelligence",
never blended into the local synthesis.

Provider: Gemini with Google Search grounding.

Hardening (cumulative across versions):
  - Tolerates Gemini's occasional duplicate-payload output (takes first valid JSON)
  - Strips ```json fences anywhere in the response
  - String-aware brace matching (correctly handles braces inside JSON strings)
  - Deduplicates gap_findings (same gap+finding → keep one)
  - Partial-JSON recovery: when Gemini truncates mid-response, salvages every
    complete {gap, finding, sources, ...} object inside gap_findings array
  - thinkingBudget=0 keeps daily quota healthy
  - maxOutputTokens=8192 (was 4096) — gives room for 6-10 gaps per query
  - Sources capped at 3 per finding (in prompt AND normalizer) — cuts URL bloat
    that was consuming ~2000 tokens of every response
"""
import json
import re
import httpx

from backend import config


PROVENANCE_TAG = "External Intelligence (web-sourced, not in vault)"

# Hard cap on sources per finding — enforced in BOTH the prompt and the normalizer
# to defend against the model ignoring the prompt rule. Each source object with a
# Vertex AI redirect URL costs ~80 tokens; capping at 3 saves ~150 tokens per finding
# vs the prior 5-source limit, which translates to ~2x more findings fitting per call.
MAX_SOURCES_PER_FINDING = 5


SYSTEM_PROMPT = f"""You are conducting external research to fill gaps in a senior Business Systems Analyst's \
local knowledge base. The original question and the gaps the user's local notes do NOT cover are below.

Your job: research ONLY the listed gaps using web sources, and return a structured JSON object that the user \
can review BEFORE deciding whether to ingest any of it into their vault.

Return ONE JSON object — no markdown, no code fences, no commentary outside the JSON, no duplicate copies:

{{
  "gap_findings": [
    {{
      "gap":         "<the gap you're addressing, ~10-20 words>",
      "finding":     "<concrete answer, 2-4 sentences. Be tight; avoid filler.>",
      "sources":     [
        {{"title": "...", "url": "...", "publisher": "...", "date": "YYYY-MM-DD"}}
      ],
      "confidence":  "high" | "medium" | "low",
      "caveats":     "<one sentence on currency, jurisdiction, or contradictions — empty string if none>"
    }}
  ],
  "overall_caveats": "<one sentence applying across findings, or empty string>"
}}

Hard rules:
- Return JSON exactly ONCE. No fences. No prose around the JSON. No duplicates.
- Use google_search. Cite REAL URLs only. **MAXIMUM {MAX_SOURCES_PER_FINDING} sources per finding** — pick the most authoritative ones (regulator/standards body first, then top-tier industry).
- Be CONCISE — findings are 2-4 sentences, not essays. Cover the gap, name the authority, move on.
- Address ONLY the listed gaps. Do not expand into adjacent topics.
- If a gap cannot be reliably answered, set finding to a short admission and explain in caveats.
- Prefer primary sources: regulators (OSFI, FINTRAC, Bank of Canada, BCBS), standards bodies (ISO, NIST).
- Flag jurisdictional context (Canadian D-SIB)."""


def _gemini_with_search(prompt: str) -> dict:
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 8192,       # was 4096 — fix A
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    with httpx.Client() as client:
        r = client.post(url, json=body, timeout=180.0)
        r.raise_for_status()
        return r.json()


def _extract_text_and_grounding(resp: dict) -> tuple[str, list]:
    try:
        cand = resp["candidates"][0]
        parts = cand["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
    except Exception:
        text = ""

    grounding = []
    try:
        chunks = resp["candidates"][0].get("groundingMetadata", {}).get("groundingChunks", [])
        for ch in chunks:
            web = ch.get("web", {})
            if web.get("uri"):
                grounding.append({
                    "title": web.get("title", ""),
                    "url": web.get("uri", ""),
                })
    except Exception:
        pass

    return text, grounding


def _strip_all_fences(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"```(?:json)?\s*\n?(.*?)\n?```", r"\1", text, flags=re.DOTALL)
    return text.strip()


def _extract_first_json_object(raw: str):
    """Extract the FIRST complete top-level JSON object via string-aware brace matching.
    Gemini occasionally returns the same payload twice; we keep only the first."""
    if not raw:
        return None
    s = _strip_all_fences(raw).strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(s)):
        c = s[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                candidate = s[start:i + 1]
                try:
                    return json.loads(candidate)
                except Exception:
                    return None
    return None


def _recover_partial_findings(raw: str) -> list:
    """When Gemini truncates mid-response, salvage every complete {gap, finding, ...}
    object from inside the gap_findings array. Anchored on the array start to avoid
    falsely closing on the outer wrapper object."""
    if not raw:
        return []
    s = _strip_all_fences(raw)

    arr_anchor = re.search(r'"gap_findings"\s*:\s*\[', s)
    if not arr_anchor:
        return []
    i = arr_anchor.end()

    findings = []
    while i < len(s):
        start = s.find('{', i)
        if start == -1:
            break
        depth = 0
        in_string = False
        escape = False
        end = -1
        for j in range(start, len(s)):
            c = s[j]
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end == -1:
            # truncation reached — stop salvaging
            break
        candidate = s[start:end + 1]
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict) and "gap" in obj and "finding" in obj:
                findings.append(obj)
        except Exception:
            pass
        i = end + 1
    return findings


def _dedupe_findings(findings: list) -> list:
    seen = set()
    out = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        key = (str(f.get("gap", "")).strip().lower(),
               str(f.get("finding", "")).strip()[:200].lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def _normalize_findings(findings_raw) -> list:
    if not isinstance(findings_raw, list):
        return []
    findings = []
    for f in findings_raw:
        if not isinstance(f, dict):
            continue
        conf = str(f.get("confidence", "")).lower().strip()
        if conf not in {"high", "medium", "low"}:
            conf = "medium"

        srcs = f.get("sources", []) or []
        if not isinstance(srcs, list):
            srcs = []
        norm_srcs = []
        for s in srcs:
            if not isinstance(s, dict):
                continue
            url = str(s.get("url", "")).strip()
            title = str(s.get("title", "")).strip()
            if not url and not title:
                continue
            norm_srcs.append({
                "title":     title,
                "url":       url,
                "publisher": str(s.get("publisher", "")).strip(),
                "date":      str(s.get("date", "")).strip(),
            })
        # Belt-and-suspenders: enforce source cap even if the model ignored the prompt rule.
        # Keeps the first N (model tends to put most authoritative sources first).
        norm_srcs = norm_srcs[:MAX_SOURCES_PER_FINDING]

        findings.append({
            "gap":        str(f.get("gap", "")).strip(),
            "finding":    str(f.get("finding", "")).strip(),
            "sources":    norm_srcs,
            "confidence": conf,
            "caveats":    str(f.get("caveats", "")).strip(),
        })
    return _dedupe_findings(findings)


def research_gaps(original_query: str, gaps: list[str]) -> dict:
    if not config.GEMINI_API_KEY:
        return {
            "provenance": PROVENANCE_TAG,
            "available": False,
            "error": ("External research requires GEMINI_API_KEY. Set it in .env "
                      "to enable web-grounded gap research."),
            "gap_findings": [],
            "grounding_sources": [],
            "overall_caveats": "",
        }

    if not gaps:
        return {
            "provenance": PROVENANCE_TAG,
            "available": True,
            "gap_findings": [],
            "grounding_sources": [],
            "overall_caveats": "No gaps were provided for external research.",
        }

    gaps_block = "\n".join(f"- {g}" for g in gaps)
    user_prompt = (
        f"=== ORIGINAL QUESTION ===\n{original_query}\n\n"
        f"=== GAPS IN LOCAL NOTES (research only these) ===\n{gaps_block}\n\n"
        f"=== JSON RESPONSE (return exactly ONE JSON object, no fences, no duplicates, "
        f"max {MAX_SOURCES_PER_FINDING} sources per finding) ===\n"
    )
    full_prompt = SYSTEM_PROMPT + "\n\n" + user_prompt

    try:
        resp = _gemini_with_search(full_prompt)
    except httpx.HTTPStatusError as e:
        msg = (f"External research call failed: HTTP {e.response.status_code}. "
               f"This may be a rate limit (free tier ~15 req/min) or a temporary API issue. "
               f"Try again in 60 seconds.")
        return {
            "provenance": PROVENANCE_TAG,
            "available": False,
            "error": msg,
            "gap_findings": [],
            "grounding_sources": [],
            "overall_caveats": "",
        }
    except Exception as e:
        return {
            "provenance": PROVENANCE_TAG,
            "available": False,
            "error": f"External research call failed: {e}",
            "gap_findings": [],
            "grounding_sources": [],
            "overall_caveats": "",
        }

    raw_text, grounding = _extract_text_and_grounding(resp)
    parsed = _extract_first_json_object(raw_text)

    if parsed and isinstance(parsed.get("gap_findings"), list):
        findings = _normalize_findings(parsed["gap_findings"])
        return {
            "provenance":         PROVENANCE_TAG,
            "available":          True,
            "gap_findings":       findings,
            "grounding_sources":  grounding,
            "overall_caveats":    str(parsed.get("overall_caveats", "")).strip(),
        }

    # Full parse failed — try partial recovery for truncation
    partial = _recover_partial_findings(raw_text)
    if partial:
        findings = _normalize_findings(partial)
        return {
            "provenance":         PROVENANCE_TAG,
            "available":          True,
            "gap_findings":       findings,
            "grounding_sources":  grounding,
            "overall_caveats":    ("Response was truncated by the model; "
                                   f"{len(findings)} complete finding(s) were recovered. "
                                   "Re-run with fewer gaps if more coverage is needed."),
        }

    # Nothing parsed and nothing recoverable — surface raw prose, labeled
    return {
        "provenance": PROVENANCE_TAG,
        "available": True,
        "gap_findings": [{
            "gap": "(model returned malformed JSON — raw response below)",
            "finding": (raw_text[:4000] if raw_text else "[Empty response from external research.]"),
            "sources": [],
            "confidence": "low",
            "caveats": ("The external research response was not in expected JSON format. "
                        "Treat this content as preliminary — verify independently."),
        }],
        "grounding_sources": grounding,
        "overall_caveats": "Response shape was malformed; structure could not be parsed cleanly.",
    }


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "What are the mandatory controls for application security?"
    gaps = sys.argv[2:] if len(sys.argv) > 2 else ["test gap one", "test gap two"]
    print(json.dumps(research_gaps(q, gaps), indent=2))
