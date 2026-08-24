#!/usr/bin/env python3
"""Strip the in-body '## How a BSA Uses This' callout from notes so stamp_apply
re-injects it uniformly with the frontmatter mirror. Idempotent & safe:
operates only on files that contain the callout; writes in place."""
import re, sys, glob, os

# block = "## How a BSA Uses This" ... through the contiguous '>' quote lines
BLOCK = re.compile(
    r'\n*##\s+How a BSA Uses This\s*\n+'      # heading
    r'(?:>.*\n?)+',                            # the contiguous blockquote callout
)

def strip_file(path):
    t = open(path, encoding="utf-8").read()
    if "How a BSA Uses This" not in t:
        return False
    new = BLOCK.sub("\n", t).rstrip() + "\n"
    if new != t:
        open(path, "w", encoding="utf-8").write(new)
        return True
    return False

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    n = 0
    for p in glob.glob(os.path.join(target, "**", "*.md"), recursive=True):
        if strip_file(p):
            print("stripped:", os.path.relpath(p, target)); n += 1
    print(f"done: {n} file(s) stripped")
