#!/usr/bin/env python3
"""
stamp_apply.py — apply pre-authored how-blocks (Path 2 / Opus-via-chat) to the vault.

Reads every batch_*.json in --blocks-dir, merges into one mapping
   { "relative/note/path.md": {elicit, specify, design, dsib}, ... }
and injects the SAME frontmatter + `## How a BSA Uses This` callout the
LLM stamper would, against a COPY of the vault.

Guarantees: never mutates originals (writes to --out), idempotent
(skips notes already carrying bsa_stamped: true), per-note safe.

Usage:
  python stamp_apply.py --vault "/path/My Second Brain" --out "/data/brain/stamped" \
                        --blocks-dir "/data/brain/batches"
"""
import os, re, json, argparse, glob, shutil

CONTRACT_VERSION = "how-v1"
FM_RE = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)

def read_note(path):
    text = open(path, encoding="utf-8", errors="ignore").read()
    m = FM_RE.match(text)
    return (m.group(1) if m else ""), (text[m.end():] if m else text)

def already(fm, body):
    return "bsa_stamped: true" in fm or "## How a BSA Uses This" in body

def yesc(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').strip() + '"'

def stamp(fm, body, j):
    add = [f"bsa_elicit: {yesc(j['elicit'])}", f"bsa_specify: {yesc(j['specify'])}",
           f"bsa_design: {yesc(j['design'])}", f"bsa_dsib: {yesc(j['dsib'])}",
           "bsa_stamped: true", f"bsa_version: {CONTRACT_VERSION}"]
    new_fm = (fm + "\n" + "\n".join(add)).strip() if fm.strip() else "\n".join(add)
    block = ("\n\n## How a BSA Uses This\n> [!bsa-how]+ How a BSA Uses This\n"
             f"> **Elicit:** {j['elicit']}\n> **Specify:** {j['specify']}\n"
             f"> **Design:** {j['design']}\n> **D-SIB Hook:** {j['dsib']}\n")
    m = re.search(r'(?m)^##\s+(Related Notes|Cross-References|Connected Notes|Linked Notes)\b', body)
    body = (body[:m.start()] + block.strip() + "\n\n" + body[m.start():]) if m else body.rstrip() + block
    return f"---\n{new_fm}\n---\n{body}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--blocks-dir", required=True)
    a = ap.parse_args()

    blocks = {}
    for fp in sorted(glob.glob(os.path.join(a.blocks_dir, "batch_*.json"))):
        blocks.update(json.load(open(fp)))
    print(f"[apply] {len(blocks)} authored how-blocks loaded")

    ok = skip = miss = 0
    for root, _, files in os.walk(a.vault):
        if ".obsidian" in root or "__MACOSX" in root: continue
        for f in files:
            if not f.endswith(".md"): continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, a.vault)
            dst = os.path.join(a.out, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            fm, body = read_note(full)
            if already(fm, body):
                shutil.copy2(full, dst); skip += 1; continue
            if rel in blocks:
                open(dst, "w", encoding="utf-8").write(stamp(fm, body, blocks[rel]))
                ok += 1
            else:
                shutil.copy2(full, dst); miss += 1   # not yet authored -> passthrough
    print(f"[apply] stamped={ok}  already={skip}  not-yet-authored={miss}")

if __name__ == "__main__":
    main()
