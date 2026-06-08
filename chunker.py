#!/usr/bin/env python3
"""
Structure-aware chunker for 'My Second Brain' -> RAG corpus.

Design principles (validated against the live 981-note corpus):
- Split on H2 (##) section boundaries  -> semantically clean chunks
- Preamble (before first H2) kept as its own chunk (holds 'what this is' + tags)
- Oversized sections (>~1000 tokens) sub-split on H3, then paragraphs, with overlap
- Tiny notes (<~40 lines) chunked whole
- Every chunk carries metadata for metadata-filtered retrieval:
    vault, note_path, note_title, section, section_index, tags, wikilinks
- Wikilinks captured as graph edges for optional graph-hop retrieval
Output: chunks.jsonl (one JSON object per line) + stats.json
"""
import re, json, hashlib, statistics
from pathlib import Path

CORPUS = Path("/tmp/sb_inspect/My Second Brain")
OUT = Path("/home/claude/brain_rag")
OUT.mkdir(exist_ok=True)

MAX_CHUNK_CHARS = 4000      # ~1000 tokens target ceiling
OVERLAP_CHARS   = 400       # ~100 token overlap when sub-splitting
MIN_NOTE_LINES_FOR_SPLIT = 40

def est_tokens(s: str) -> int:
    return max(1, len(s) // 4)

def clean_header(h: str) -> str:
    return re.sub(r'^#+\s*', '', re.sub(r'[*_`]', '', h)).strip()

def note_metadata(text: str, path: Path):
    rel = path.relative_to(CORPUS)
    vault = rel.parts[0] if len(rel.parts) > 1 else "(root)"
    tags = sorted(set(re.findall(r'(?:^|\s)#([A-Za-z0-9_\-/]+)', text)))
    wikilinks = sorted(set(l.split('|')[0].split('#')[0].strip()
                           for l in re.findall(r'\[\[([^\]]+)\]\]', text)))
    return vault, str(rel), path.stem, tags, wikilinks

def split_oversized(body: str):
    """Sub-split a large section on H3, then paragraphs, with overlap."""
    if len(body) <= MAX_CHUNK_CHARS:
        return [body]
    # try H3 first
    h3parts = re.split(r'(?m)(^###\s+.*$)', body)
    if len(h3parts) > 1:
        merged, cur = [], ""
        for seg in h3parts:
            if len(cur) + len(seg) <= MAX_CHUNK_CHARS:
                cur += seg
            else:
                if cur.strip(): merged.append(cur)
                cur = seg
        if cur.strip(): merged.append(cur)
        if all(len(m) <= MAX_CHUNK_CHARS for m in merged):
            return merged
    # fall back to paragraph windows with overlap
    paras = body.split("\n\n")
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 2 <= MAX_CHUNK_CHARS:
            cur += ("\n\n" if cur else "") + p
        else:
            if cur.strip(): chunks.append(cur)
            tail = cur[-OVERLAP_CHARS:] if cur else ""
            cur = (tail + "\n\n" + p) if tail else p
    if cur.strip(): chunks.append(cur)
    return chunks

def chunk_note(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    vault, relpath, title, tags, wikilinks = note_metadata(text, path)
    nlines = text.count("\n") + 1
    out = []

    def mk(section, idx, content):
        content = content.strip()
        if not content:
            return
        cid = hashlib.sha1(f"{relpath}::{idx}::{content[:80]}".encode()).hexdigest()[:16]
        out.append({
            "chunk_id": cid,
            "vault": vault,
            "note_path": relpath,
            "note_title": title,
            "section": section,
            "section_index": idx,
            "tags": tags,
            "wikilinks": wikilinks,
            "char_count": len(content),
            "est_tokens": est_tokens(content),
            "text": content,
        })

    # tiny note -> whole
    if nlines < MIN_NOTE_LINES_FOR_SPLIT and text.count("\n## ") == 0:
        mk("(whole note)", 0, text)
        return out

    # split on H2
    parts = re.split(r'(?m)(^##\s+.*$)', text)
    # parts[0] = preamble; then alternating (header, body)
    idx = 0
    if parts[0].strip():
        mk("(preamble)", idx, parts[0]); idx += 1
    for i in range(1, len(parts), 2):
        header = clean_header(parts[i])
        body = parts[i] + "\n" + (parts[i+1] if i+1 < len(parts) else "")
        for sub in split_oversized(body):
            mk(header, idx, sub); idx += 1
    return out

def main():
    all_chunks, edges = [], 0
    notes = sorted(CORPUS.rglob("*.md"))
    # skip obsidian/system
    notes = [n for n in notes if ".obsidian" not in n.parts and "__MACOSX" not in str(n)]
    per_vault = {}
    for n in notes:
        cs = chunk_note(n)
        all_chunks.extend(cs)
        v = cs[0]["vault"] if cs else "?"
        per_vault[v] = per_vault.get(v, 0) + len(cs)
        if cs: edges += len(cs[0]["wikilinks"])

    with open(OUT / "chunks.jsonl", "w") as f:
        for c in all_chunks:
            f.write(json.dumps(c) + "\n")

    toks = [c["est_tokens"] for c in all_chunks]
    in_band = sum(1 for t in toks if 80 <= t <= 1000)
    stats = {
        "notes_processed": len(notes),
        "total_chunks": len(all_chunks),
        "avg_chunks_per_note": round(len(all_chunks)/len(notes), 1),
        "chunk_tokens_min": min(toks),
        "chunk_tokens_median": int(statistics.median(toks)),
        "chunk_tokens_max": max(toks),
        "pct_in_target_band_80_1000": round(100*in_band/len(toks), 1),
        "total_wikilink_edges": edges,
        "chunks_per_vault": dict(sorted(per_vault.items(), key=lambda x: -x[1])),
    }
    with open(OUT / "stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print(json.dumps(stats, indent=2))
    print("\n--- SAMPLE CHUNK (with metadata) ---")
    sample = next(c for c in all_chunks if 300 < c["est_tokens"] < 700)
    s = dict(sample); s["text"] = s["text"][:500] + " ...[truncated]"
    print(json.dumps(s, indent=2))

if __name__ == "__main__":
    main()
