#!/usr/bin/env python3
"""Check which requested gene symbols have a RefSeq Select transcript.

Run this BEFORE the scan. Parsing the full GFF with pyranges takes minutes and
loads ~900 MB; this streams the file and looks only at mRNA lines carrying the
"RefSeq Select" tag, which is the same filter the analysis applies. It answers
the gate question — which symbols are missing — in seconds rather than minutes.

Matching is exact and case-insensitive. A substring match would silently pull
in neighbours (Cat matching Cat1), and a user handed a gene list has no way to
see that happen in the output.

Usage:
    python check_genes.py <genomic.gff> --genes Spic Nfe2l2 Hmox1
    python check_genes.py <genomic.gff> --genes-file panel.txt

Prints a JSON report on stdout and a human summary on stderr.
Exit 0 whether or not genes are missing — deciding what to do is the agent's
job, not this script's. Exit 1 only on a real error.
"""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

GENE_RE = re.compile(r"(?:^|;)gene=([^;]+)")
TXID_RE = re.compile(r"(?:^|;)transcript_id=([^;]+)")
ID_RE = re.compile(r"(?:^|;)ID=([^;]+)")


def uniprot_url(symbol: str, taxon: int | None = None) -> str:
    q = symbol if taxon is None else f"{symbol} AND (taxonomy_id:{taxon})"
    return f"https://www.uniprot.org/uniprotkb?query={quote(q)}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("gff", type=Path)
    ap.add_argument("--genes", nargs="*", default=[])
    ap.add_argument("--genes-file", type=Path, default=None,
                    help="one symbol per line; blank lines and # comments ignored")
    ap.add_argument("--taxon", type=int, default=10090,
                    help="NCBI taxon id used in the UniProt links (default mouse)")
    ap.add_argument("--progress-every", type=int, default=2_000_000,
                    help="GFF lines between progress messages")
    args = ap.parse_args()

    requested: list[str] = list(args.genes)
    if args.genes_file:
        for line in args.genes_file.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                requested.append(line)
    # de-duplicate, preserve the order the user gave
    requested = list(dict.fromkeys(requested))
    if not requested:
        print("FAIL  no genes requested", file=sys.stderr)
        return 1
    if not args.gff.is_file():
        print(f"FAIL  GFF not found: {args.gff}", file=sys.stderr)
        return 1

    wanted = {g.lower(): g for g in requested}
    found: dict[str, list[dict]] = {g: [] for g in requested}

    print(f"      scanning {args.gff.name} for RefSeq Select mRNA records "
          f"({len(requested)} symbols requested)...", file=sys.stderr)

    n = 0
    with args.gff.open("rt", errors="replace") as fh:
        for line in fh:
            n += 1
            if n % args.progress_every == 0:
                hits = sum(bool(v) for v in found.values())
                print(f"      ...{n:,} lines, {hits}/{len(requested)} symbols matched",
                      file=sys.stderr)
            if line.startswith("#"):
                continue
            # cheap rejects before any splitting, since most lines are exons
            if "RefSeq Select" not in line:
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 9 or parts[2] != "mRNA":
                continue
            attrs = parts[8]
            m = GENE_RE.search(attrs)
            if not m:
                continue
            sym = m.group(1)
            key = sym.lower()
            if key not in wanted:
                continue
            tx = TXID_RE.search(attrs) or ID_RE.search(attrs)
            found[wanted[key]].append({
                "chromosome": parts[0],
                "start": int(parts[3]),
                "end": int(parts[4]),
                "strand": parts[6],
                "transcript_id": tx.group(1) if tx else None,
                "gff_symbol": sym,
            })

    missing = [g for g in requested if not found[g]]
    multi = {g: len(v) for g, v in found.items() if len(v) > 1}

    report = {
        "gff": str(args.gff),
        "lines_read": n,
        "requested": requested,
        "found": {g: v for g, v in found.items() if v},
        "missing": missing,
        "multiple_transcripts": multi,
        "uniprot_links": {g: uniprot_url(g, args.taxon) for g in missing},
    }

    ok = len(requested) - len(missing)
    print(f"      {ok}/{len(requested)} symbols have a RefSeq Select transcript",
          file=sys.stderr)
    if multi:
        # The analysis keeps all of them; say so rather than letting the
        # promoter count come out unexplained.
        detail = ", ".join(f"{g} x{c}" for g, c in sorted(multi.items()))
        print(f"      note: more than one RefSeq Select record for {detail} "
              f"(all are kept, as in the original analysis)", file=sys.stderr)
    if missing:
        print(f"      missing: {', '.join(missing)}", file=sys.stderr)

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
