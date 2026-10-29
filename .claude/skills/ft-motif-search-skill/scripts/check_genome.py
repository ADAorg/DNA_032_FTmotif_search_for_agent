#!/usr/bin/env python3
"""Verify the reference genome is present, complete and current.

The agent must not fall back to a partial genome: a truncated FASTA yields
short or missing promoters and the scan still "succeeds", which is the
failure mode worth refusing outright.

NCBI's own dataset_catalog.json records the uncompressed byte size of every
file it shipped, so it is the authoritative check and it is small enough to
live in the repo. assembly_data_report.jsonl carries the annotation release,
which is what distinguishes a current reference from a stale one.

Usage:
    python check_genome.py <refseq_dir> [--expect-annotation NAME]

Exit 0 with a JSON report on stdout if everything checks out, exit 1 otherwise.
"""
import argparse
import json
import sys
from pathlib import Path


def find(directory: Path, name: str) -> Path | None:
    """Locate a catalog file, flat or one level down.

    NCBI's catalog lists paths under an accession subdirectory, but the files
    are commonly moved up a level after download. Accept either.
    """
    direct = directory / name
    if direct.is_file():
        return direct
    hits = sorted(directory.glob(f"*/{name}"))
    return hits[0] if hits else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("refseq_dir", type=Path)
    ap.add_argument("--expect-annotation", default=None,
                    help="annotation release the analysis was validated against")
    args = ap.parse_args()

    d = args.refseq_dir
    problems: list[str] = []
    report: dict = {"refseq_dir": str(d)}

    if not d.is_dir():
        print(f"FAIL  not a directory: {d}", file=sys.stderr)
        return 1

    catalog_path = d / "dataset_catalog.json"
    if not catalog_path.is_file():
        print(f"FAIL  dataset_catalog.json missing from {d}\n"
              f"      Without it there is no way to confirm the genome is complete.\n"
              f"      Re-download with: datasets download genome accession "
              f"<ACCESSION> --include genome,gff3", file=sys.stderr)
        return 1

    catalog = json.loads(catalog_path.read_text())

    # Expected sizes, keyed by basename so a flattened layout still matches.
    expected: dict[str, int] = {}
    accession = None
    for asm in catalog.get("assemblies", []):
        accession = asm.get("accession", accession)
        for f in asm.get("files", []):
            if f.get("fileType") in {"GENOMIC_NUCLEOTIDE_FASTA", "GFF3"}:
                expected[Path(f["filePath"]).name] = int(f["uncompressedLengthBytes"])
    report["accession"] = accession

    if not expected:
        print("FAIL  catalog lists no genome FASTA or GFF3 entry", file=sys.stderr)
        return 1

    checked = {}
    for name, want in sorted(expected.items()):
        path = find(d, name)
        if path is None:
            problems.append(f"{name}: not found under {d}")
            checked[name] = {"status": "missing", "expected_bytes": want}
            continue
        got = path.stat().st_size
        ok = got == want
        checked[name] = {"status": "ok" if ok else "size_mismatch",
                         "path": str(path), "expected_bytes": want, "actual_bytes": got}
        if not ok:
            delta = got - want
            problems.append(
                f"{name}: {got:,} bytes, expected {want:,} ({delta:+,}). "
                + ("Truncated — the download did not finish."
                   if delta < 0 else "Larger than shipped — not the file NCBI released.")
            )
    report["files"] = checked

    # Annotation release: a complete file can still be an outdated annotation.
    adr = find(d, "assembly_data_report.jsonl")
    if adr is not None:
        first = adr.read_text().strip().split("\n")[0]
        info = json.loads(first)
        ann = info.get("annotationInfo", {}).get("name")
        asm_name = info.get("assemblyInfo", {}).get("assemblyName")
        status = info.get("assemblyInfo", {}).get("assemblyStatus")
        report["annotation"] = ann
        report["assembly_name"] = asm_name
        report["assembly_status"] = status
        if args.expect_annotation and ann != args.expect_annotation:
            problems.append(
                f"annotation release is {ann}, expected {args.expect_annotation}. "
                "Coordinates may differ from the validated run."
            )
        if status and status != "current":
            problems.append(f"assembly status is {status!r}, not 'current'")
    else:
        report["annotation"] = None

    report["ok"] = not problems
    report["problems"] = problems

    if problems:
        print("FAIL  genome check did not pass:", file=sys.stderr)
        for p in problems:
            print(f"      - {p}", file=sys.stderr)
        print("\n      Refusing to run. Fix the genome rather than scanning a partial one.",
              file=sys.stderr)
        print(json.dumps(report, indent=2))
        return 1

    fasta = next((v["path"] for k, v in checked.items() if k.endswith((".fna", ".fa", ".fasta"))), None)
    gff = next((v["path"] for k, v in checked.items() if k.endswith((".gff", ".gff3"))), None)
    report["fasta"] = fasta
    report["gff"] = gff

    print(f"OK    genome complete: {accession} {report.get('assembly_name')} "
          f"({report.get('annotation')})", file=sys.stderr)
    for name, v in sorted(checked.items()):
        print(f"      {name}  {v['actual_bytes']:,} bytes", file=sys.stderr)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
