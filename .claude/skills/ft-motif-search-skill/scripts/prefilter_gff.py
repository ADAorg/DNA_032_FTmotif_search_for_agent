#!/usr/bin/env python3
"""Write the RefSeq Select mRNA records of the annotation to a small GFF.

The notebook only ever uses mRNA records tagged "RefSeq Select" (cell
`gtf_import`). Parsing the full 920 MB GFF with pyranges to get them needs
several GB of RAM — more than a chat sandbox has, where it is OOM-killed — and
minutes everywhere else. This streams the full GFF once and keeps only the
lines that filter could possibly keep: column 3 == "mRNA" and "RefSeq Select"
anywhere on the line. That is a superset of the notebook's filter, and the
notebook still applies its own filter afterwards, so the records it selects
are the same as from the full file.

Output, next to the source:  genomic.refseq_select_mrna.gff
Its header records the source file name, size and SHA-256, so the notebook can
refuse a file built from a different annotation:

    ##gff-version 3
    #!prefilter source=genomic.gff.gz size=51298029 sha256=<hex> filter=mRNA+RefSeq_Select records=21002

Usage:
    python prefilter_gff.py <genomic.gff | genomic.gff.gz>

Use the `gff` path printed by check_genome.py. Re-running is cheap: if the
output already exists and was built from this exact source, it is left alone.
Prints a JSON report on stdout; exit 1 on error.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sys
from pathlib import Path

OUT_NAME = "genomic.refseq_select_mrna.gff"
FILTER = "mRNA+RefSeq_Select"
HEADER_RE = re.compile(r"^#!prefilter source=(\S+) size=(\d+) sha256=([0-9a-f]{64}) "
                       r"filter=(\S+) records=(\d+)")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_header(path: Path) -> dict | None:
    """The #!prefilter line of an existing output, or None."""
    try:
        with open(path) as fh:
            for _ in range(5):
                m = HEADER_RE.match(fh.readline())
                if m:
                    return dict(zip(("source", "size", "sha256", "filter", "records"),
                                    m.groups()))
    except OSError:
        pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("gff", type=Path, help="full genomic.gff or genomic.gff.gz")
    ap.add_argument("--force", action="store_true", help="rebuild even if up to date")
    args = ap.parse_args()

    src = args.gff
    if not src.is_file():
        print(f"FAIL  GFF not found: {src}", file=sys.stderr)
        return 1
    out = src.parent / OUT_NAME
    size = src.stat().st_size

    print(f"      hashing {src.name} ({size:,} bytes)...", file=sys.stderr)
    digest = sha256(src)

    existing = read_header(out)
    if (not args.force and existing and existing["source"] == src.name
            and int(existing["size"]) == size and existing["sha256"] == digest
            and existing["filter"] == FILTER):
        print(f"OK    {out.name} already built from this {src.name} "
              f"({int(existing['records']):,} records)", file=sys.stderr)
        print(json.dumps({"ok": True, "gff": str(out), "source": str(src),
                          "records": int(existing["records"]), "rebuilt": False}, indent=2))
        return 0

    print(f"      streaming {src.name} for mRNA records tagged RefSeq Select...",
          file=sys.stderr)
    kept: list[str] = []
    n = 0
    opener = gzip.open if src.suffix == ".gz" else open
    with opener(src, "rt") as fh:
        for line in fh:
            n += 1
            if line.startswith("#") or "RefSeq Select" not in line:
                continue
            parts = line.split("\t")
            if len(parts) == 9 and parts[2] == "mRNA":
                kept.append(line if line.endswith("\n") else line + "\n")

    if not kept:
        print(f"FAIL  no RefSeq Select mRNA records in {src.name} — wrong or truncated "
              "annotation", file=sys.stderr)
        return 1

    # write to a temp name and rename, so an interrupted run never leaves a
    # half-written file that looks valid
    tmp = out.with_suffix(".gff.tmp")
    with open(tmp, "w") as fh:
        fh.write("##gff-version 3\n")
        fh.write(f"#!prefilter source={src.name} size={size} sha256={digest} "
                 f"filter={FILTER} records={len(kept)}\n")
        fh.writelines(kept)
    os.replace(tmp, out)

    print(f"OK    wrote {out.name}: {len(kept):,} records from {n:,} lines", file=sys.stderr)
    print(json.dumps({"ok": True, "gff": str(out), "source": str(src),
                      "records": len(kept), "rebuilt": True}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
