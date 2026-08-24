#!/usr/bin/env python3
"""
stamp_apply.py -- apply pre-authored how-blocks to the vault.

Reads every batch_*.json in --blocks-dir, merges into one mapping
   { "relative/note/path.md": {elicit, specify, design, dsib[, failure, verify]}, ... }
and injects frontmatter + a `## How a BSA Uses This` callout against a COPY
of the vault.

Guarantees: never mutates originals (writes to --out), idempotent
(skips notes already carrying bsa_stamped: true), per-note safe.

v2 changes:
  - `failure` and `verify` are supported as OPTIONAL fields
  - unknown keys in a batch now WARN instead of being silently dropped
  - missing required keys WARN and the note is skipped rather than crashing
  - bsa_version reflects which contract the note was stamped under

Usage:
  python3 stamp_apply.py --vault ~/brain/source-vault --out ~/brain/stamped \
                         --blocks-dir ~/brain/second-brain-rag/batches
"""
import os, re, json, argparse, glob, shutil

REQUIRED = ["elicit", "specify", "design", "dsib"]
OPTIONAL = ["failure", "verify"]
KNOWN = REQUIRED + OPTIONAL

LABELS = {
    "elicit":  "Elicit",
    "specify": "Specify",
    "design":  "Design",
    "dsib":    "D-SIB Hook",
    "failure": "Failure Mode",
    "verify":  "Verify",
}

V1 = "how-v1"   # four fields
V2 = "how-v2"   # four + any optional

FM_RE = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)


def read_note(path):
    text = open(path, encoding="utf-8", errors="ignore").read()
    m = FM_RE.match(text)
    return (m.group(1) if m else ""), (text[m.end():] if m else text)


def already(fm, body):
    return "bsa_stamped: true" in fm or "## How a BSA Uses This" in body


def yesc(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').strip() + '"'


def stamp(fm, body, j):
    present = [f for f in KNOWN if j.get(f)]
    version = V2 if any(f in OPTIONAL for f in present) else V1

    add = [f"bsa_{f}: {yesc(j[f])}" for f in present]
    add += ["bsa_stamped: true", f"bsa_version: {version}"]
    new_fm = (fm + "\n" + "\n".join(add)).strip() if fm.strip() else "\n".join(add)

    lines = "".join(f"> **{LABELS[f]}:** {j[f]}\n" for f in present)
    block = ("\n\n## How a BSA Uses This\n> [!bsa-how]+ How a BSA Uses This\n"
             + lines)

    m = re.search(r'(?m)^##\s+(Related Notes|Cross-References|Connected Notes|Linked Notes)\b', body)
    body = (body[:m.start()] + block.strip() + "\n\n" + body[m.start():]) if m else body.rstrip() + block
    return f"---\n{new_fm}\n---\n{body}"


def load_blocks(blocks_dir):
    blocks, warn_unknown, warn_missing = {}, [], []
    for fp in sorted(glob.glob(os.path.join(blocks_dir, "batch_*.json"))):
        data = json.load(open(fp, encoding="utf-8"))
        data.pop("_schema", None)          # allow a metadata block in a batch
        for k, v in data.items():
            if not isinstance(v, dict):
                continue
            unknown = [f for f in v if f not in KNOWN]
            missing = [f for f in REQUIRED if not v.get(f)]
            if unknown:
                warn_unknown.append((os.path.basename(fp), k, unknown))
            if missing:
                warn_missing.append((os.path.basename(fp), k, missing))
                continue                    # do not stamp a partial block
            blocks[k] = v
    for fn, k, u in warn_unknown:
        print(f"[warn] {fn}: unknown field(s) {u} on {k} -- will be IGNORED")
    for fn, k, m in warn_missing:
        print(f"[warn] {fn}: missing required {m} on {k} -- note SKIPPED")
    return blocks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--blocks-dir", required=True)
    a = ap.parse_args()

    blocks = load_blocks(a.blocks_dir)
    n_v2 = sum(1 for v in blocks.values() if any(f in v for f in OPTIONAL))
    print(f"[apply] {len(blocks)} authored how-blocks loaded  ({n_v2} carry optional fields)")

    ok = skip = miss = 0
    for root, _, files in os.walk(a.vault):
        if ".obsidian" in root or "__MACOSX" in root:
            continue
        for f in files:
            if not f.endswith(".md"):
                continue
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
                shutil.copy2(full, dst); miss += 1
    print(f"[apply] stamped={ok}  already={skip}  not-yet-authored={miss}")


if __name__ == "__main__":
    main()
