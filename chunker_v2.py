#!/usr/bin/env python3
"""
chunker_v2.py — frontmatter-aware, structure-aware chunker for the stamped
Second Brain corpus. Emits content chunks + typed how_layer chunks.

This version has:
  - MAX_CHUNK_CHARS=1800 (fits mxbai-embed-large's 512-token window comfortably)
  - hard force-cut for blocks (e.g. giant tables) that have no natural splits
  - Mac paths pre-set (edit if your username differs)
"""
import re, json, hashlib, statistics
from pathlib import Path

# === EDIT THESE TWO IF YOUR USERNAME DIFFERS ================================
CORPUS = Path(os.getenv("CORPUS_DIR", os.path.expanduser("~/brain/stamped")))
OUT    = Path(os.getenv("OUT_DIR", os.path.expanduser("~/brain/second-brain-rag")))
# ============================================================================

OUT.mkdir(exist_ok=True)

MAX_CHUNK_CHARS = 1000
OVERLAP_CHARS   = 200
MIN_NOTE_LINES_FOR_SPLIT = 40

HOW_HEADER = "## How a BSA Uses This"
FM_RE = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)
FM_KV_RE = re.compile(r'^(bsa_[a-z_]+):\s*(.*)$')


def est_tokens(s: str) -> int:
    return max(1, len(s) // 4)


def clean_header(h: str) -> str:
    return re.sub(r'^#+\s*', '', re.sub(r'[*_`]', '', h)).strip()


def parse_frontmatter(text: str):
    m = FM_RE.match(text)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        kv = FM_KV_RE.match(line.strip())
        if not kv:
            continue
        key, raw = kv.group(1), kv.group(2).strip()
        if raw in ("true", "false"):
            fm[key] = (raw == "true")
        else:
            v = raw
            if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                v = v[1:-1]
            fm[key] = v.replace('\\"', '"').replace('\\\\', '\\')
    return fm, text[m.end():]


def bsa_meta(fm: dict) -> dict:
    return {
        "bsa_stamped": bool(fm.get("bsa_stamped", False)),
        "bsa_version": fm.get("bsa_version"),
        "bsa_elicit":  fm.get("bsa_elicit"),
        "bsa_specify": fm.get("bsa_specify"),
        "bsa_design":  fm.get("bsa_design"),
        "bsa_dsib":    fm.get("bsa_dsib"),
    }


def note_metadata(text: str, body: str, path: Path):
    rel = path.relative_to(CORPUS)
    vault = rel.parts[0] if len(rel.parts) > 1 else "(root)"
    tags = sorted(set(re.findall(r'(?:^|\s)#([A-Za-z0-9_\-/]+)', body)))
    wikilinks = sorted(set(l.split('|')[0].split('#')[0].strip()
                           for l in re.findall(r'\[\[([^\]]+)\]\]', body)))
    return vault, str(rel), path.stem, tags, wikilinks


def extract_how_block(body: str):
    idx = body.find(HOW_HEADER)
    if idx == -1:
        return body, None
    after = body[idx + len(HOW_HEADER):]
    nxt = re.search(r'(?m)^##\s+', after)
    end = idx + len(HOW_HEADER) + (nxt.start() if nxt else len(after))
    how_block = body[idx:end].strip()
    body_wo = (body[:idx] + body[end:]).strip()
    return body_wo, how_block


def split_oversized(body: str):
    """Split a section into chunks <= MAX_CHUNK_CHARS, with overlap.
    Force-cuts any block (e.g. giant table) that has no natural split points."""
    if len(body) <= MAX_CHUNK_CHARS:
        return [body]

    # try splitting on h3 headers first
    h3parts = re.split(r'(?m)(^###\s+.*$)', body)
    if len(h3parts) > 1:
        merged, cur = [], ""
        for seg in h3parts:
            if len(cur) + len(seg) <= MAX_CHUNK_CHARS:
                cur += seg
            else:
                if cur.strip():
                    merged.append(cur)
                cur = seg
        if cur.strip():
            merged.append(cur)
        if all(len(m) <= MAX_CHUNK_CHARS for m in merged):
            return merged

    # otherwise split on paragraphs with overlap
    paras = body.split("\n\n")
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 2 <= MAX_CHUNK_CHARS:
            cur += ("\n\n" if cur else "") + p
        else:
            if cur.strip():
                chunks.append(cur)
            tail = cur[-OVERLAP_CHARS:] if cur else ""
            cur = (tail + "\n\n" + p) if tail else p
    if cur.strip():
        chunks.append(cur)

    # hard force-cut for blocks that still exceed limit (e.g. giant tables)
    final = []
    for c in chunks:
        while len(c) > MAX_CHUNK_CHARS:
            final.append(c[:MAX_CHUNK_CHARS])
            c = c[MAX_CHUNK_CHARS - OVERLAP_CHARS:]
        if c.strip():
            final.append(c)
    return final


def chunk_note(path: Path):
    raw = path.read_text(encoding="utf-8", errors="ignore")
    fm, body = parse_frontmatter(raw)
    meta = bsa_meta(fm)
    body, how_block = extract_how_block(body)
    vault, relpath, title, tags, wikilinks = note_metadata(raw, body, path)
    nlines = body.count("\n") + 1
    out = []

    def mk(section, idx, content, chunk_type="content"):
        content = content.strip()
        if not content:
            return
        cid = hashlib.sha1(f"{relpath}::{idx}::{content[:80]}".encode()).hexdigest()[:16]
        rec = {
            "chunk_id": cid,
            "chunk_type": chunk_type,
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
        }
        rec.update(meta)
        out.append(rec)

    if nlines < MIN_NOTE_LINES_FOR_SPLIT and body.count("\n## ") == 0:
        mk("(whole note)", 0, body)
    else:
        parts = re.split(r'(?m)(^##\s+.*$)', body)
        idx = 0
        if parts[0].strip():
            mk("(preamble)", idx, parts[0])
            idx += 1
        for i in range(1, len(parts), 2):
            header = clean_header(parts[i])
            sec_body = parts[i] + "\n" + (parts[i + 1] if i + 1 < len(parts) else "")
            for sub in split_oversized(sec_body):
                mk(header, idx, sub)
                idx += 1

    if how_block:
        mk("How a BSA Uses This", 9000, how_block, chunk_type="how_layer")

    return out


def main():
    notes = sorted(CORPUS.rglob("*.md"))
    notes = [n for n in notes if ".obsidian" not in n.parts and "__MACOSX" not in str(n)]
    all_chunks, edges = [], 0
    per_vault = {}
    for n in notes:
        cs = chunk_note(n)
        all_chunks.extend(cs)
        v = cs[0]["vault"] if cs else "?"
        per_vault[v] = per_vault.get(v, 0) + len(cs)
        if cs:
            edges += len(cs[0]["wikilinks"])

    with open(OUT / "chunks.jsonl", "w") as f:
        for c in all_chunks:
            f.write(json.dumps(c) + "\n")

    toks = [c["est_tokens"] for c in all_chunks]
    in_band = sum(1 for t in toks if 80 <= t <= 1000)
    how_chunks = [c for c in all_chunks if c["chunk_type"] == "how_layer"]
    stamped_notes = len({c["note_path"] for c in all_chunks if c.get("bsa_stamped")})
    stats = {
        "notes_processed": len(notes),
        "total_chunks": len(all_chunks),
        "content_chunks": sum(1 for c in all_chunks if c["chunk_type"] == "content"),
        "how_layer_chunks": len(how_chunks),
        "stamped_notes": stamped_notes,
        "avg_chunks_per_note": round(len(all_chunks) / len(notes), 1),
        "chunk_tokens_min": min(toks),
        "chunk_tokens_median": int(statistics.median(toks)),
        "chunk_tokens_max": max(toks),
        "pct_in_target_band_80_1000": round(100 * in_band / len(toks), 1),
        "total_wikilink_edges": edges,
        "chunks_per_vault": dict(sorted(per_vault.items(), key=lambda x: -x[1])),
    }
    with open(OUT / "stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
