#!/usr/bin/env python3
"""RSAT matrix-scan wrapper: CIS-BP matrices, order-1 background, promoter scan.

This is the notebook's scan path extracted into a module, with two changes and
one preserved workaround. Import it, or run it from the command line.

Changed from the notebook
-------------------------
1. Promoter selection is an EXACT match on the gene field of the FASTA header,
   not a substring test against the whole header. The original
   `any(g.lower() in i.lower() ...)` is safe only because an earlier exact
   filter already narrowed the FASTA to the requested panel; given an
   arbitrary gene list it would silently pull in neighbours (Cat -> Cat1) with
   nothing in the output to show it happened.
2. Every requested gene must match at least one promoter, else it raises. A
   typo should fail loudly, not scan 31 promoters when 32 were asked for.

Preserved workaround
--------------------
matrix-scan's own -bginput is broken: it exits reporting "the sum must be
strictly positive" and then divides by zero in RSAT/matrix.pm. Confirmed in
bioconda rsat-core 2025.04.04 and still in 2026.10.08, so this is permanent,
not a patch waiting to be removed. The background is therefore estimated with
oligo-analysis and passed via -bgfile: the same estimator over the same
sequences, just made explicit.

Also note matrix-scan can print "Error" on stdout while exiting 0, so the
return code alone is not a sufficient check. `_rsat()` greps for it.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

DEFAULT_PVALUE = 1e-4
DEFAULT_MARKOV = 1
DEFAULT_PSEUDO = 1
DEFAULT_BG_PSEUDO = 0.01


def log(msg: str) -> None:
    print(f"      {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------------
# RSAT environment
# --------------------------------------------------------------------------
class RSAT:
    """Locate an RSAT install and run its tools.

    rsat-core is a Perl suite dispatched through a single `rsat` entry point;
    there is no standalone matrix-scan on PATH (only matrix-scan-quick, which
    is a different program). The env's bin must lead PATH or the shebang
    resolves to the system perl and the tool dies on missing modules.
    """

    def __init__(self, prefix: str | Path | None = None):
        self.prefix = Path(prefix) if prefix else self._discover()
        self.bin = self.prefix / "bin" / "rsat"
        if not self.bin.is_file():
            raise FileNotFoundError(
                f"no rsat dispatcher at {self.bin}\n"
                "Create the environment with:\n"
                "  conda create -n rsat -c bioconda -c conda-forge rsat-core\n"
                "Note bioconda ships rsat-core for linux-64, linux-aarch64 and "
                "osx-64 but NOT osx-arm64; on Apple Silicon use "
                "CONDA_SUBDIR=osx-64 or a container."
            )
        self.env = os.environ | {
            "PATH": f"{self.prefix / 'bin'}{os.pathsep}{os.environ['PATH']}",
            "RSAT": str(self.prefix / "share" / "rsat"),
            "CONDA_PREFIX": str(self.prefix),
        }

    @staticmethod
    def _discover() -> Path:
        """Find an rsat env without being told where it is."""
        env_var = os.environ.get("RSAT_ENV")
        if env_var:
            return Path(env_var)
        on_path = shutil.which("rsat")
        if on_path:
            return Path(on_path).resolve().parent.parent
        candidates = []
        for root in (Path.home() / ".conda" / "envs",
                     Path.home() / "miniconda3" / "envs",
                     Path.home() / "anaconda3" / "envs",
                     Path("/opt/conda/envs")):
            if root.is_dir():
                candidates += [p for p in root.iterdir() if (p / "bin" / "rsat").is_file()]
        if candidates:
            return candidates[0]
        raise FileNotFoundError(
            "no RSAT environment found. Set RSAT_ENV=/path/to/env, or create one:\n"
            "  conda create -n rsat -c bioconda -c conda-forge rsat-core"
        )

    def __call__(self, tool: str, *args) -> str:
        cmd = [str(self.bin), tool, *map(str, args)]
        p = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
        out = p.stderr + p.stdout
        # Some tools report failure on stdout while exiting 0.
        if p.returncode or re.search(r"^Error", out, re.M):
            raise RuntimeError(f"RSAT {tool} failed\n$ {' '.join(cmd)}\n{out}")
        return out

    def version(self) -> str:
        for line in (self.prefix / "conda-meta").glob("rsat-core-*.json"):
            return line.stem.replace("rsat-core-", "")
        return "unknown"


# --------------------------------------------------------------------------
# Matrices
# --------------------------------------------------------------------------
def cisbp_to_transfac(cisbp_dir: Path, motifs: dict[str, str], out: Path) -> Path:
    """Convert CIS-BP probability matrices to TRANSFAC counts.

    CIS-BP gives probabilities (rows sum to 1). Scaling by 100 makes them
    count-like so that matrix-scan's -pseudo 1 stays a small correction
    instead of dominating the column.

    motifs maps CIS-BP accession -> the label used in output, e.g.
    {"M03221_3.10": "Spic"}.
    """
    blocks = []
    for acc, label in motifs.items():
        path = cisbp_dir / f"{acc}.txt"
        if not path.is_file():
            raise FileNotFoundError(f"CIS-BP matrix not found: {path}")
        m = pd.read_csv(path, sep="\t")
        rows = [f"{i:02d}\t" + "\t".join(f"{v * 100:.4f}" for v in r)
                for i, r in enumerate(m[["A", "C", "G", "T"]].values, start=1)]
        blocks.append(f"AC  {acc}\nXX\nID  {label}\nXX\nDE  {label}\n"
                      "P0\tA\tC\tG\tT\n" + "\n".join(rows) + "\nXX\n//\n")
        log(f"{acc:<14} {len(m)} bp -> {label}")
    out.write_text("".join(blocks))
    return out


def subset_matrices(matrix_file: Path, labels: list[str], out: Path) -> Path:
    blocks = [b.strip() + "\n//\n" for b in matrix_file.read_text().split("//")
              if (m := re.search(r"^ID\s+(\S+)\s*$", b, re.M)) and m.group(1) in labels]
    if len(blocks) != len(labels):
        got = re.findall(r"^ID\s+(\S+)\s*$", matrix_file.read_text(), re.M)
        raise ValueError(f"wanted matrices {labels}, found {got}")
    out.write_text("".join(blocks))
    return out


# --------------------------------------------------------------------------
# FASTA
# --------------------------------------------------------------------------
def read_fasta(path: Path) -> list[tuple[str, str]]:
    """[(header_without_'>', sequence), ...]"""
    recs, head, buf = [], None, []
    for line in Path(path).read_text().splitlines():
        if line.startswith(">"):
            if head is not None:
                recs.append((head, "".join(buf)))
            head, buf = line[1:].strip(), []
        elif head is not None:
            buf.append(line.strip())
    if head is not None:
        recs.append((head, "".join(buf)))
    return recs


def select_promoters(records, genes: list[str] | None):
    """Exact, case-insensitive match on the gene field of 'Gene|Transcript'.

    Returns (selected, missing). See the module docstring for why this is not
    a substring test.
    """
    if not genes:
        return list(records), []
    wanted = {g.lower(): g for g in genes}
    hit: dict[str, list] = {g: [] for g in genes}
    for header, seq in records:
        sym = header.split("|", 1)[0].strip().lstrip(">")
        if sym.lower() in wanted:
            hit[wanted[sym.lower()]].append((header, seq))
    selected = [r for g in genes for r in hit[g]]
    missing = [g for g in genes if not hit[g]]
    return selected, missing


# --------------------------------------------------------------------------
# Scan
# --------------------------------------------------------------------------
def matrix_scan(fasta: Path, matrix_file: Path, labels: list[str], out_ft: Path,
                genes: list[str] | None = None, pvalue: float = DEFAULT_PVALUE,
                markov: int = DEFAULT_MARKOV, pseudo: int = DEFAULT_PSEUDO,
                bg_pseudo: float = DEFAULT_BG_PSEUDO, bg_from: str = "input",
                rsat: RSAT | None = None, keep_inputs: Path | None = None
                ) -> pd.DataFrame:
    """Scan promoters for the given matrices. Returns the 'site' rows.

    bg_from: "input" estimates the background from the selected promoters,
    "all" from every promoter in the FASTA.
    """
    rsat = rsat or RSAT()
    out_ft.parent.mkdir(parents=True, exist_ok=True)

    records = read_fasta(fasta)
    selected, missing = select_promoters(records, genes)
    if missing:
        raise ValueError(
            f"no promoter in {fasta.name} for: {', '.join(missing)}. "
            "Check the gene check step ran and the FASTA is current."
        )
    if not selected:
        raise ValueError(f"no promoters selected from {fasta}")
    log(f"{len(selected)} promoters selected from {len(records)} in {fasta.name}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(keep_inputs) if keep_inputs else Path(tmpdir)
        tmp.mkdir(parents=True, exist_ok=True)

        mat = subset_matrices(matrix_file, labels, tmp / "matrices.tf")
        seqs = tmp / "promoters.fasta"
        seqs.write_text("".join(f">{h}\n{s}\n" for h, s in selected))

        bg_src = fasta if bg_from == "all" else seqs
        log(f"estimating order-{markov} background from "
            f"{'all promoters' if bg_from == 'all' else 'the selected promoters'}...")
        bg = tmp / "bg.tab"
        # -bginput is broken in rsat-core; see module docstring.
        rsat("oligo-analysis", "-i", bg_src, "-l", markov + 1, "-1str",
             "-return", "occ,freq", "-o", bg)

        log(f"scanning {len(selected)} promoters x {len(labels)} matrices "
            f"at p <= {pvalue:g} (both strands)...")
        rsat("matrix-scan", "-v", 1,
             "-i", seqs, "-seq_format", "fasta",
             "-m", mat, "-matrix_format", "transfac",
             "-bgfile", bg, "-bg_pseudo", bg_pseudo, "-pseudo", pseudo,
             "-2str", "-origin", "end", "-n", "score",
             "-return", "limits", "-return", "sites", "-return", "pval",
             "-uth", "pval", pvalue, "-o", out_ft)

    all_rows = pd.read_csv(out_ft, sep="\t", comment=";")
    hits = all_rows.query("ft_type == 'site'").copy()
    hits.attrs["scan_path"] = str(out_ft)
    log(f"{len(hits)} sites at p <= {pvalue:g}")
    return hits


def rsat_parameters(ft_path: Path) -> str:
    """The ';' header of a .ft.txt: the authoritative parameter record.

    pd.read_csv(..., comment=';') discards exactly these lines, which is why
    the run's real background order and pseudo-counts are easy to lose.
    """
    return "\n".join(l for l in Path(ft_path).read_text().splitlines()
                     if l.startswith(";"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fasta", type=Path, help="promoter FASTA, headers 'Gene|TranscriptID'")
    ap.add_argument("matrices", type=Path, help="TRANSFAC matrix file")
    ap.add_argument("-l", "--labels", nargs="+", required=True, help="matrix IDs to scan")
    ap.add_argument("-g", "--genes", nargs="*", default=None, help="genes to scan; default all")
    ap.add_argument("-o", "--out", type=Path, required=True, help="output .ft.txt")
    ap.add_argument("-p", "--pvalue", type=float, default=DEFAULT_PVALUE)
    ap.add_argument("--markov", type=int, default=DEFAULT_MARKOV)
    ap.add_argument("--bg-from", choices=["input", "all"], default="input")
    ap.add_argument("--rsat-env", default=None)
    args = ap.parse_args()

    rsat = RSAT(args.rsat_env)
    log(f"rsat-core {rsat.version()} at {rsat.prefix}")
    hits = matrix_scan(args.fasta, args.matrices, args.labels, args.out,
                       genes=args.genes, pvalue=args.pvalue, markov=args.markov,
                       bg_from=args.bg_from, rsat=rsat)
    csv = args.out.with_suffix(".sites.csv")
    hits.to_csv(csv, index=False)
    log(f"wrote {args.out} and {csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
