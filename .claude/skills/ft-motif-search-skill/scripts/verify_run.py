#!/usr/bin/env python3
"""Check that a finished run matches what was asked for, before it is packaged.

Why this exists: in a test run the notebook's last cell rendered the committed
notebook instead of the run's copy. That re-ran the repository's default panel
(37 genes, 5 kb) over the run's outputs and left a tracked file modified. Every
file the contract lists was present, so `package_results.py` would have zipped
it, and a checklist item cannot catch it because the agent ticks the box while
holding the wrong results. So this compares what the run *produced* with what
the run *recorded asking for* in its own run_config.yaml.

It is read-only. It changes nothing.

Checks:
  * run_config.yaml names the genes, the upstream window, the p-value, the motifs
  * promoters_sequences.fasta holds exactly the requested genes, every sequence
    exactly upstream + 201 bp (a window running past a contig end comes back
    short, and is reported rather than scanned)
  * the hits table and the raw scan mention no gene that was not requested, and
    no hit is above the requested p-value
  * the raw scan used the requested p-value threshold and only the chosen motifs
  * no tracked file in the repository changed, and nothing new appeared in it
    outside the run directory

Usage:
    python verify_run.py <run_dir> [--repo PATH]

Exit 0 if nothing failed (warnings are printed), exit 1 otherwise.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # JSON is accepted too, so the check still runs
    yaml = None

DOWNSTREAM_PLUS_TSS = 201      # 200 bp downstream + the TSS base itself


def _load_config(run_dir: Path):
    path = run_dir / "run_config.yaml"
    if not path.is_file():
        return None, [f"FAIL  run_config.yaml is missing from {run_dir}; the run does not record what it was asked for"]
    text = path.read_text()
    try:
        cfg = yaml.safe_load(text) if yaml else json.loads(text)
    except Exception as e:  # noqa: BLE001 - any parse error is a failure of the record
        return None, [f"FAIL  run_config.yaml could not be read ({e}); install pyyaml if it is YAML"]
    a = (cfg or {}).get("analysis") or {}
    out, problems = {}, []
    genes = a.get("genes") or []
    if not genes:
        problems.append("FAIL  run_config.yaml lists no genes. A run with no recorded panel may be using the notebook's default panel")
    out["genes"] = [str(g) for g in genes]
    up = a.get("promoter_upstream_bp")
    if not isinstance(up, int) or isinstance(up, bool):
        problems.append(f"FAIL  run_config.yaml has no whole-number promoter_upstream_bp (got {up!r})")
    out["upstream"] = up
    pv = a.get("pvalue")
    if not isinstance(pv, (int, float)):
        problems.append(f"FAIL  run_config.yaml has no numeric pvalue (got {pv!r})")
    out["pvalue"] = pv
    motifs = a.get("motifs") or []
    if not motifs:
        problems.append("FAIL  run_config.yaml lists no motifs")
    out["motifs"] = [str(m) for m in motifs]
    return (None if problems else out), problems


def _gene_of(header: str) -> str:
    return header.lstrip(">").split("|", 1)[0].strip()


def _check_fasta(run_dir: Path, genes, upstream):
    path = run_dir / "promoters_sequences.fasta"
    if not path.is_file():
        return [f"FAIL  promoters_sequences.fasta is missing from {run_dir}"]
    want = {g.lower(): g for g in genes}
    seen: dict[str, str] = {}
    lengths: list[tuple[str, int]] = []
    head, n = None, 0

    def close():
        if head is not None:
            lengths.append((head, n))
            seen.setdefault(_gene_of(head).lower(), _gene_of(head))

    with path.open() as fh:
        for line in fh:
            if line.startswith(">"):
                close()
                head, n = line[1:].strip(), 0
            elif head is not None:
                n += len(line.strip())
    close()

    out = []
    missing = [want[k] for k in want if k not in seen]
    extra = [seen[k] for k in seen if k not in want]
    if missing:
        out.append(f"FAIL  promoters: requested genes with no promoter: {', '.join(sorted(missing))}")
    if extra:
        shown = ", ".join(sorted(extra)[:12]) + (" …" if len(extra) > 12 else "")
        out.append(f"FAIL  promoters: {len(extra)} genes that were NOT requested are in the run "
                   f"({shown}). This is what a run overwritten by the default panel looks like")
    expect = upstream + DOWNSTREAM_PLUS_TSS if isinstance(upstream, int) else None
    if expect is not None:
        bad = [(h, ln) for h, ln in lengths if ln != expect]
        if bad:
            sample = "; ".join(f"{h}: {ln} bp" for h, ln in bad[:4])
            out.append(f"FAIL  promoters: {len(bad)} of {len(lengths)} sequences are not {expect} bp "
                       f"({upstream} upstream + {DOWNSTREAM_PLUS_TSS}). {sample}. "
                       "A window running past a contig end comes back short")
    if not (missing or extra or (expect is not None and any(ln != expect for _, ln in lengths))):
        out.append(f"OK    promoters: {len(seen)} genes, exactly the {len(want)} requested; "
                   f"{len(lengths)} sequences x {expect} bp ({upstream} upstream + {DOWNSTREAM_PLUS_TSS})")
    return out


def _check_hits(run_dir: Path, genes, pvalue):
    files = sorted(run_dir.glob("motifs_coordinates_*.csv"))
    if not files:
        return ["FAIL  hits table (motifs_coordinates_*.csv) is missing from the run directory"]
    want = {g.lower() for g in genes}
    out = []
    for path in files:
        with path.open(newline="") as fh:
            rows = list(csv.DictReader(fh))
        if rows and "Gene_Name" not in rows[0]:
            out.append(f"WARN  hits table {path.name}: no Gene_Name column; gene check skipped")
            continue
        extra = sorted({r["Gene_Name"] for r in rows if r["Gene_Name"].lower() not in want})
        over = []
        if isinstance(pvalue, (int, float)) and rows and "Pval" in rows[0]:
            for r in rows:
                try:
                    if float(r["Pval"]) > pvalue * 1.001:
                        over.append(r["Pval"])
                except ValueError:
                    pass
        if extra:
            out.append(f"FAIL  hits table {path.name}: genes that were not requested: {', '.join(extra[:12])}")
        if over:
            out.append(f"FAIL  hits table {path.name}: {len(over)} hits above the requested p-value {pvalue:g}")
        if not extra and not over:
            out.append(f"OK    hits table {path.name}: {len(rows)} sites, every gene requested, none above p {pvalue:g}")
    return out


def _parse_ft(path: Path):
    thr, sites = None, []
    with path.open(errors="replace") as fh:
        for line in fh:
            if line.startswith(";"):
                m = re.match(r";\s*pval\s+\S+\s+(\S+)", line) or re.search(r"-uth\s+pval\s+(\S+)", line)
                if m and thr is None:
                    try:
                        thr = float(m.group(1))
                    except ValueError:
                        pass
                continue
            if line.startswith("#") or not line.strip():
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) >= 3 and f[1] == "site":
                sites.append((_gene_of(f[0]), f[2]))
    return thr, sites


def _check_ft(run_dir: Path, genes, motifs, pvalue):
    files = sorted((run_dir / "matrix_scan").glob("scanmotif_*.ft"))
    if not files:
        return ["FAIL  raw scan (matrix_scan/scanmotif_*.ft) is missing from the run directory"]
    want_g = {g.lower() for g in genes}
    want_m = {m.lower() for m in motifs}
    out = []
    for path in files:
        thr, sites = _parse_ft(path)
        bad = []
        if thr is None:
            out.append(f"WARN  raw scan {path.name}: no p-value threshold in its header; threshold check skipped")
        elif isinstance(pvalue, (int, float)) and not math.isclose(thr, pvalue, rel_tol=1e-6):
            bad.append(f"scanned at p <= {thr:g} but the run asked for {pvalue:g}")
        xg = sorted({g for g, _ in sites if g.lower() not in want_g})
        xm = sorted({m for _, m in sites if m.lower() not in want_m})
        if xg:
            bad.append(f"genes that were not requested: {', '.join(xg[:12])}")
        if xm:
            bad.append(f"motifs that were not chosen: {', '.join(xm)}")
        if bad:
            out += [f"FAIL  raw scan {path.name}: {b}" for b in bad]
        else:
            out.append(f"OK    raw scan {path.name}: p <= {thr:g}, {len(sites)} sites, only the chosen motifs and requested genes")
    return out


def _check_repo(run_dir: Path, repo):
    here = Path(__file__).resolve().parent
    try:
        root = Path(repo) if repo else Path(subprocess.run(
            ["git", "-C", str(here), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True).stdout.strip())
        res = subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                             capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return ["WARN  could not run git here, so the repository was NOT confirmed unchanged"]
    changed = []
    for line in res.stdout.splitlines():
        rel = line[3:].split(" -> ")[-1].strip().strip('"')
        p = (root / rel).resolve()
        try:
            p.relative_to(run_dir)
            continue                      # inside the run directory: expected
        except ValueError:
            changed.append(line)
    if changed:
        shown = "; ".join(changed[:6]) + (" …" if len(changed) > 6 else "")
        return [f"FAIL  repository changed during the run ({len(changed)} paths: {shown}). "
                "A run must leave tracked files byte-for-byte unchanged; start again from a fresh clone"]
    return ["OK    repository unchanged (git status clean outside the run directory)"]


def _check_report(run_dir: Path):
    reports = sorted(run_dir.glob("*_report.html"))
    if not reports:
        return []                          # the packaging contract reports a missing report
    text = reports[0].read_text(errors="replace")
    if "genomic.refseq_select_mrna.gff" in text:
        return ["OK    report names genomic.refseq_select_mrna.gff as the annotation read"]
    return ["WARN  report does not name genomic.refseq_select_mrna.gff; the prefilter step may have been skipped "
            "(same result, but the full GFF parse needs ~11 GB of RAM)"]


def verify(run_dir: Path, repo=None):
    run_dir = Path(run_dir).resolve()
    cfg, lines = _load_config(run_dir)
    if cfg is not None:
        lines += [f"OK    run_config.yaml: {len(cfg['genes'])} genes, {cfg['upstream']} bp upstream, "
                  f"p <= {cfg['pvalue']:g}, motifs {', '.join(cfg['motifs'])}"]
        lines += _check_fasta(run_dir, cfg["genes"], cfg["upstream"])
        lines += _check_hits(run_dir, cfg["genes"], cfg["pvalue"])
        lines += _check_ft(run_dir, cfg["genes"], cfg["motifs"], cfg["pvalue"])
    lines += _check_repo(run_dir, repo)
    lines += _check_report(run_dir)
    return not any(l.startswith("FAIL") for l in lines), lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--repo", default=None, help="repository root (default: found from this script's location)")
    args = ap.parse_args()
    if not args.run_dir.is_dir():
        print(f"FAIL  not a directory: {args.run_dir}", file=sys.stderr)
        return 1
    ok, lines = verify(args.run_dir, args.repo)
    for line in lines:
        print(line, file=sys.stderr)
    print("\nPASS" if ok else "\nFAIL  the run does not match what was asked for", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
