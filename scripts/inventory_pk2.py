#!/usr/bin/env python3
"""Read-only PK2 inventory built from pk2_mate `list` output.

pk2_mate's `list` prints directories as full paths indented by the cumulative
character length of their parent path, and files as bare names indented at the
parent directory's child indent (see pk2_mate/src/main.rs:337 `list_files`,
pinned commit e07dec0667bfed9c998cf582416f87ee2e85e6bb). This parser reverses
that layout into exact internal paths. It does NOT implement a PK2 reader; it
only parses the verified reader's text output.

The listing carries no per-file sizes, so file counts come from the listing and
total sizes must come from controlled extraction (measured separately).

Usage:
    python3 scripts/inventory_pk2.py path/to/Data.list.txt [--json]
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def parse_listing(text):
    """Return (files, dirs): lists of exact internal paths.

    Algorithm (mirrors pk2_mate): a stack holds (dir_path, child_indent)
    where child_indent = printed indent + len(printed path). Both directories
    and files are printed at their parent's child_indent, so to find the parent
    of any line we pop stack entries whose child_indent != line indent.
    """
    files, dirs = [], []
    stack = [("/", 0)]
    for raw in text.splitlines():
        if not raw.strip():
            continue
        stripped = raw.lstrip(" ")
        indent = len(raw) - len(stripped)
        while len(stack) > 1 and stack[-1][1] != indent:
            stack.pop()
        if stripped.startswith("/"):
            path = stripped
            dirs.append(path)
            stack.append((path, indent + len(path)))
        else:
            parent = stack[-1][0] if stack else "/"
            files.append(parent.rstrip("/") + "/" + stripped if parent != "/" else "/" + stripped)
    return files, dirs


def extension_groups(files):
    by_ext = Counter()
    by_top = Counter()
    total = 0
    for f in files:
        total += 1
        name = f.rsplit("/", 1)[-1]
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else "(none)"
        by_ext[ext] += 1
        top = f.split("/")[1] if f.startswith("/") and len(f) > 1 else "(root)"
        by_top[top] += 1
    return by_ext, by_top, total


def main():
    parser = argparse.ArgumentParser(description="Parse pk2_mate list output into inventory")
    parser.add_argument("listing", help="Path to pk2_mate list output (.txt)")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--max-ext", type=int, default=25, help="Max extension rows in text output")
    args = parser.parse_args()

    text = Path(args.listing).read_text(encoding="utf-8", errors="replace")
    files, dirs = parse_listing(text)
    by_ext, by_top, total = extension_groups(files)

    if args.json:
        json.dump(
            {
                "listing": args.listing,
                "file_count": total,
                "dir_count": len(dirs),
                "by_extension": dict(by_ext.most_common()),
                "by_top_level": dict(by_top.most_common()),
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return

    print("listing : {0}".format(args.listing))
    print("files   : {0}".format(total))
    print("dirs    : {0}".format(len(dirs)))
    print("by top-level:")
    for top, n in by_top.most_common():
        print("  {0:20s} {1}".format(top, n))
    print("by extension (top {0}):".format(args.max_ext))
    for ext, n in by_ext.most_common(args.max_ext):
        print("  .{0:10s} {1}".format(ext, n))


if __name__ == "__main__":
    main()
