#!/usr/bin/env python3
"""Build the results zip, and refuse to build an incomplete one.

Why this exists: packaging used to be described in SKILL.md and implemented
separately in the notebook. The two drifted — the notebook zipped whatever sat
in Results/results_report/ (four files) while the documented contract listed
nine, and nothing noticed. A checklist item cannot catch that, because the
agent ticks it while running the shorter code. So the contract lives here, as
code, and a missing file is an error rather than a quieter zip.

This is the ONLY way to build the zip. The notebook no longer packages.

The patterns below are the names the notebook writes when run with
DNA032_RESULTS pointing at the run directory, plus the run record written by
runconfig.py. If a filename changes in the notebook, change it here too —
this list is the enforced copy of the contract; SKILL.md and docs/SOP.md
describe it.

Usage:
    python package_results.py <run_dir> [--zip-name NAME] [--allow-missing PATTERN ...]

Exit 0 and print the zip path if every required artefact is present; exit 1
listing what is absent otherwise.
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

# The contract: (glob, human description). Every entry is required.
CONTRACT: list[tuple[str, str]] = [
    ("*_report.html",            "HTML report"),
    ("sitemap_*.svg",            "site map (SVG)"),
    ("sitemap_*.png",            "site map (PNG)"),
    ("sitemap_*.pdf",            "site map (PDF)"),
    ("motifs_coordinates_*.csv", "hits table (CSV)"),
    ("scanmotif_*.ft",           "raw RSAT output, ';' header intact"),
    ("my_settings.yaml",         "the user's choices"),
    ("run_config.yaml",          "choices plus locked method parameters"),
    ("run_log.md",               "what actually happened in the run"),
    ("requested_changes.md",     "changes the user asked for beyond the four choices"),
]


def find(run_dir: Path, pattern: str) -> list[Path]:
    """Files matching pattern anywhere under run_dir, one per filename.

    The notebook writes some outputs twice (matrix_scan/ and results_report/);
    keep the shallowest copy of each name so the zip holds no duplicates.
    """
    best: dict[str, Path] = {}
    for p in sorted(run_dir.rglob(pattern), key=lambda p: (len(p.parts), str(p))):
        if p.is_file() and p.name not in best:
            best[p.name] = p
    return sorted(best.values())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--zip-name", default=None)
    ap.add_argument("--allow-missing", nargs="*", default=[],
                    help="globs that may legitimately be absent for this run; "
                         "each one is reported in the output so the omission is visible")
    args = ap.parse_args()

    run_dir: Path = args.run_dir.resolve()
    if not run_dir.is_dir():
        print(f"FAIL  not a directory: {run_dir}", file=sys.stderr)
        return 1

    known = {pattern for pattern, _ in CONTRACT}
    unknown = set(args.allow_missing) - known
    if unknown:
        print(f"FAIL  --allow-missing names patterns not in the contract: "
              f"{', '.join(sorted(unknown))}\n      valid: {', '.join(sorted(known))}",
              file=sys.stderr)
        return 1

    waived = set(args.allow_missing)
    found: list[tuple[str, Path]] = []
    missing: list[tuple[str, str]] = []
    waived_absent: list[str] = []

    for pattern, desc in CONTRACT:
        hits = find(run_dir, pattern)
        if hits:
            found += [(desc, h) for h in hits]
        elif pattern in waived:
            waived_absent.append(f"{desc} ({pattern})")
        else:
            missing.append((pattern, desc))

    if missing:
        print("FAIL  the run is incomplete — not packaging it:", file=sys.stderr)
        for pattern, desc in missing:
            print(f"      - {desc}  (no file matching {pattern} under {run_dir})",
                  file=sys.stderr)
        print("\n      Produce these before packaging. Do not hand over a partial zip,\n"
              "      do not assemble one by hand, and do not describe it as complete.",
              file=sys.stderr)
        return 1

    name = args.zip_name or f"results_{run_dir.name}.zip"
    out = run_dir / name
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for _, path in found:
            z.write(path, path.name)

    print(f"OK    {out}", file=sys.stderr)
    for desc, path in found:
        print(f"      {path.name}  ({desc})", file=sys.stderr)
    if waived_absent:
        print("      deliberately omitted:", file=sys.stderr)
        for w in waived_absent:
            print(f"      - {w}", file=sys.stderr)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
