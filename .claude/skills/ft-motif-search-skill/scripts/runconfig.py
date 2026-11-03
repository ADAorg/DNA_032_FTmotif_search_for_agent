#!/usr/bin/env python3
"""Run configuration: what a user may change, and what is fixed.

The analysis parameters are part of a published method. Someone re-running it
should be able to choose which transcription factors and genes to scan, and
how the figures look, without being able to quietly alter how the scan itself
is performed — a changed background order or pseudo-count produces results
that look valid and are not comparable.

So settings fall into two sets:

  SETTABLE  transcription factors, gene panel, p-value, upstream promoter
            length, and everything about presentation (colours, figure size,
            formats, labels).

  LOCKED    background model and order, pseudo-counts, strand handling,
            coordinate origin, downstream promoter length, transcript
            selection, matrix scaling. Changing any of these changes the method.

The downstream length stays locked because -origin end places the TSS at
-(downstream + 1); keeping it fixed means the upstream length can change
without shifting any reported coordinate.

A user config that touches a locked key is rejected with the maintainer's
contact address rather than silently ignored, because silently ignoring it
would produce a report that does not match what the user asked for.

Every run writes its full resolved configuration — settable and locked
together — so the report always carries the parameters that produced it.

Usage:
    python runconfig.py --init my_settings.yaml      # write a starter config
    python runconfig.py --check my_settings.yaml     # validate without running
    python runconfig.py --log RUN_DIR --settings RUN_DIR/my_settings.yaml \
        --promoters re-extracted --genome-check passed   # write run_log.md
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:  # fall back to JSON so the skill still works
    yaml = None

MAINTAINER = "sara.salazar@gimm.pt"

# --------------------------------------------------------------------------
# The method. Not user-settable.
# --------------------------------------------------------------------------
LOCKED: dict = {
    "species": "Mus musculus",
    "genome_accession": "GCF_000001635.27",
    "genome_assembly": "GRCm39",
    "annotation_release": "GCF_000001635.27-RS_2024_02",
    "markov_order": 1,
    "pseudo_count": 1,
    "bg_pseudo_frequency": 0.01,
    "background_from": "input",
    "strands": "both",
    "origin": "end",
    "promoter_downstream_bp": 200,
    "transcript_filter": "RefSeq Select",
    "matrix_scaling": 100,
    "gene_match": "exact",
}

LOCKED_WHY: dict[str, str] = {
    "species": "the analysis is validated for mouse only",
    "genome_accession": "coordinates, promoters and transcript IDs are all specific to this assembly",
    "genome_assembly": "a different build shifts every coordinate in the report",
    "annotation_release": "transcript selection depends on the annotation release",
    "markov_order": "the published method uses a first-order Markov background",
    "pseudo_count": "pseudo-count 1, distributed proportionally to residue priors",
    "bg_pseudo_frequency": "affects background estimation; fixed at the RSAT form default",
    "background_from": "the background is estimated from the scanned promoters",
    "strands": "both strands are scanned",
    "origin": "coordinates are negative from the sequence end; coupled to the TSS offset",
    "promoter_downstream_bp": "it sets the TSS offset (-origin end); changing it shifts every coordinate",
    "transcript_filter": "canonical transcripts only",
    "matrix_scaling": "makes CIS-BP probabilities count-like so the pseudo-count stays small",
    "gene_match": "exact matching prevents a gene symbol pulling in its neighbours",
}

# --------------------------------------------------------------------------
# Defaults for everything a user may change.
# --------------------------------------------------------------------------
SETTABLE_DEFAULTS: dict = {
    "analysis": {
        "motifs": ["Spic", "Nfe2l2_1", "Nfe2l2_2", "Bach1"],
        "genes": [],
        "pvalue": 1e-4,
        "promoter_upstream_bp": 2000,   # 200 bp downstream is locked
    },
    "figure": {
        "colors": {
            "Spic": "#E64B35",
            "Nfe2l2_1": "#4DBBD5",
            "Nfe2l2_2": "#00A087",
            "Bach1": "#3C5488",
        },
        "width_in": 9.0,
        "row_height_in": 0.33,
        "dpi": 300,
        "formats": ["svg", "png", "pdf"],
        "title": None,
        "tss_line_color": "#C1272D",
        "track_color": "#DEDEDE",
        "sort_promoters_by": "input",   # "input" | "name" | "n_sites"
        "label_font_size": 10,
        "show_legend": True,
    },
    "output": {
        "zip_name": None,          # default: motif_scan_<timestamp>.zip
        "include_raw_ft": True,
        "include_logos": True,
    },
}

SORT_CHOICES = {"input", "name", "n_sites"}
FORMAT_CHOICES = {"svg", "png", "pdf"}


class LockedSettingError(Exception):
    """Raised when a config tries to change the method."""


def _deep_merge(base: dict, override: dict, path: str = "") -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        here = f"{path}.{k}" if path else k
        if k not in out:
            raise LockedSettingError(
                f"unknown setting {here!r}\n"
                f"  Settable sections are: {', '.join(SETTABLE_DEFAULTS)}.\n"
                f"  If you need this changed, contact {MAINTAINER}."
            )
        if isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v, here)
        else:
            out[k] = v
    return out


def validate(cfg: dict) -> list[str]:
    """Return a list of problems; empty means valid."""
    problems: list[str] = []
    a, f, o = cfg["analysis"], cfg["figure"], cfg["output"]

    p = a.get("pvalue")
    if not isinstance(p, (int, float)) or not (0 < p <= 0.1):
        problems.append(f"analysis.pvalue must be a number in (0, 0.1]; got {p!r}")
    up = a.get("promoter_upstream_bp")
    if isinstance(up, bool) or not isinstance(up, int) or up < 1000:
        problems.append(f"analysis.promoter_upstream_bp must be a whole number of bp, at least 1000; got {up!r}")
    if not a.get("motifs"):
        problems.append("analysis.motifs is empty — choose at least one transcription factor")

    if f.get("sort_promoters_by") not in SORT_CHOICES:
        problems.append(f"figure.sort_promoters_by must be one of {sorted(SORT_CHOICES)}")
    bad = set(f.get("formats", [])) - FORMAT_CHOICES
    if bad:
        problems.append(f"figure.formats: unsupported {sorted(bad)}; choose from {sorted(FORMAT_CHOICES)}")
    for name, val, lo, hi in (("figure.width_in", f.get("width_in"), 3, 30),
                              ("figure.row_height_in", f.get("row_height_in"), 0.1, 2),
                              ("figure.dpi", f.get("dpi"), 72, 1200),
                              ("figure.label_font_size", f.get("label_font_size"), 4, 32)):
        if not isinstance(val, (int, float)) or not (lo <= val <= hi):
            problems.append(f"{name} must be between {lo} and {hi}; got {val!r}")
    for motif, color in (f.get("colors") or {}).items():
        if not (isinstance(color, str) and color.startswith("#") and len(color) in (4, 7)):
            problems.append(f"figure.colors[{motif!r}] must be a hex colour like '#E64B35'; got {color!r}")

    if not isinstance(o.get("include_raw_ft"), bool):
        problems.append("output.include_raw_ft must be true or false")
    return problems


def load(path: str | Path | None) -> dict:
    """Merge a user config over the defaults, refusing locked keys."""
    cfg = copy.deepcopy(SETTABLE_DEFAULTS)
    if path is None:
        return cfg
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"config not found: {path}")
    text = path.read_text()
    user = (yaml.safe_load(text) if yaml else json.loads(text)) or {}
    if not isinstance(user, dict):
        raise LockedSettingError(f"{path} should contain a mapping of settings")

    # Names people reach for when they mean a locked setting. Mapping them
    # explicitly gives the real explanation instead of "unknown setting".
    ALIASES = {
        "genome": "genome_accession", "reference": "genome_accession",
        "assembly": "genome_assembly", "build": "genome_assembly",
        "genome_build": "genome_assembly", "accession": "genome_accession",
        "fasta": "genome_accession", "gff": "annotation_release",
        "gtf": "annotation_release", "annotation": "annotation_release",
        "organism": "species", "taxon": "species",
        "markov": "markov_order", "background": "background_from",
        "pseudo": "pseudo_count",
        "downstream": "promoter_downstream_bp", "strand": "strands",
    }

    # A locked key at any level is the case worth a clear message.
    def scan_locked(d: dict, path_str: str = "") -> None:
        for k, v in d.items():
            k = ALIASES.get(k, k)
            if k in LOCKED:
                why = LOCKED_WHY.get(k, "this is part of the published method")
                raise LockedSettingError(
                    f"{k!r} cannot be changed here — {why}.\n\n"
                    f"  The method parameters are fixed so that results stay comparable\n"
                    f"  between runs and match the published analysis. You can change\n"
                    f"  which transcription factors and genes are scanned, the p-value,\n"
                    f"  the upstream promoter length, and anything about the figures.\n\n"
                    f"  If your work genuinely needs a different {k}, please contact\n"
                    f"  {MAINTAINER} rather than editing the analysis."
                )
            if isinstance(v, dict):
                scan_locked(v, f"{path_str}.{k}" if path_str else k)

    scan_locked(user)
    merged = _deep_merge(cfg, user)
    problems = validate(merged)
    if problems:
        raise LockedSettingError("invalid configuration:\n  - " + "\n  - ".join(problems))
    return merged


def resolved(cfg: dict) -> dict:
    """Settable config plus the locked method, for the run record."""
    out = copy.deepcopy(cfg)
    out["method_locked"] = copy.deepcopy(LOCKED)
    out["recorded_at"] = datetime.now().isoformat(timespec="seconds")
    return out


def save_settings(cfg: dict, path: str | Path) -> Path:
    """Write just the user-settable part, so it can be shared and reused.

    This is the file a user hands back: it fully describes what they changed
    and nothing about the method, so it can be applied to any copy of the
    analysis without carrying hidden differences.
    """
    path = Path(path)
    body = {k: cfg[k] for k in SETTABLE_DEFAULTS}
    header = (
        "# Promoter motif scan — user settings\n"
        "#\n"
        "# These are the settings you may change: which transcription factors and\n"
        "# genes to scan, the p-value, the upstream promoter length, and how the\n"
        "# figures look.\n"
        "#\n"
        "# Method parameters (background model, pseudo-counts, downstream length,\n"
        f"# strand handling) are fixed. To discuss changing one, contact {MAINTAINER}.\n"
        "#\n"
        "# Share this file to let someone reproduce your run exactly.\n\n"
    )
    if yaml:
        path.write_text(header + yaml.safe_dump(body, sort_keys=False, allow_unicode=True))
    else:
        path.write_text(json.dumps(body, indent=2))
    return path


def save_run_record(cfg: dict, path: str | Path) -> Path:
    """Write the full resolved configuration for the run directory."""
    path = Path(path)
    rec = resolved(cfg)
    if yaml:
        path.write_text(yaml.safe_dump(rec, sort_keys=False, allow_unicode=True))
    else:
        path.write_text(json.dumps(rec, indent=2))
    return path


def changes_from_defaults(cfg: dict) -> list[tuple[str, object, object]]:
    """Settable values that differ from SETTABLE_DEFAULTS, as (key, default, value).

    analysis.genes is left out: it has no meaningful default, every run
    supplies it, and the run log lists the panel on its own. Computed here
    rather than by eye so the same config always yields the same list.
    """
    out: list[tuple[str, object, object]] = []

    def walk(default: dict, value: dict, path: str) -> None:
        for k, d in default.items():
            here = f"{path}.{k}" if path else k
            if here == "analysis.genes":
                continue
            v = value.get(k, d)
            if isinstance(d, dict) and isinstance(v, dict):
                walk(d, v, here)
            elif v != d:
                out.append((here, d, v))

    walk(SETTABLE_DEFAULTS, cfg, "")
    return out


def _git_state(repo: Path) -> str:
    """Commit and cleanliness of the checkout, for the run log."""
    import subprocess
    try:
        commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                               capture_output=True, text=True, check=True).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        return "unknown (not a git checkout)"
    if dirty:
        return f"{commit} — **{len(dirty)} uncommitted change(s) in the repository**"
    return f"{commit} (clean)"


def write_run_log(cfg: dict, path: str | Path, *, promoters: str, genome_check: str,
                  repo: str | Path = ".", replaced: list[str] | None = None,
                  unticked: list[str] | None = None, annotation: str | None = None) -> Path:
    """Write run_log.md: what was run, what differs from the defaults, what was not ticked.

    promoters is "re-extracted" or "reused:<path to FASTA>". Written on every
    run, not only when something changed, so a missing log is never mistaken
    for "no changes". annotation is the GFF file the notebook read (the full
    genomic.gff or the prefilter_gff.py output); recorded so the log says which.
    """
    if promoters == "re-extracted":
        prom = "re-extracted from the genome in this run"
    elif promoters.startswith("reused:"):
        prom = (f"**reused from `{promoters[len('reused:'):]}` — not regenerated "
                "in this run** (genome unavailable)")
    else:
        raise ValueError("promoters must be 're-extracted' or 'reused:<path>'")

    path = Path(path)
    a = cfg["analysis"]
    lines = [
        f"# Run log — {path.parent.name}",
        "",
        f"- Recorded: {datetime.now().isoformat(timespec='seconds')}",
        f"- Repository commit: {_git_state(Path(repo))}",
        f"- Genome check: {genome_check}",
        f"- Annotation file read: {annotation or 'not recorded'}",
        "",
        "## What was run",
        "",
        f"- Motifs: {', '.join(a['motifs'])}",
        f"- Genes ({len(a['genes'])}): {', '.join(a['genes']) or '—'}",
        f"- Gene check replacements: {'; '.join(replaced) if replaced else 'none'}",
        f"- Promoter window: -{a['promoter_upstream_bp']} / +{LOCKED['promoter_downstream_bp']} bp",
        f"- p-value: {a['pvalue']:g}",
        f"- Promoters: {prom}",
        "- Locked method: unchanged (full values in `run_config.yaml`)",
        "",
        "## Changes from defaults",
        "",
    ]
    changes = changes_from_defaults(cfg)
    if changes:
        lines += ["| Setting | Default | This run |", "|---|---|---|"]
        lines += [f"| `{k}` | `{d!r}` | `{v!r}` |" for k, d, v in changes]
    else:
        lines.append("None — every setting is at its default.")
    lines += ["", "## Checklist items not ticked", ""]
    lines += [f"- {u}" for u in unticked] if unticked else ["None."]
    path.write_text("\n".join(lines) + "\n")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--init", metavar="PATH", help="write a starter settings file")
    g.add_argument("--check", metavar="PATH", help="validate a settings file")
    g.add_argument("--log", metavar="RUN_DIR", help="write RUN_DIR/run_log.md")
    ap.add_argument("--settings", metavar="PATH", help="(--log) the run's my_settings.yaml")
    ap.add_argument("--promoters", metavar="SOURCE", help="(--log) 're-extracted' or 'reused:<fasta>'")
    ap.add_argument("--genome-check", metavar="RESULT", help="(--log) e.g. 'passed' or 'not available'")
    ap.add_argument("--replaced", nargs="*", default=[], metavar="OLD=NEW",
                    help="(--log) gene check outcomes, e.g. Nrf2=Nfe2l2 Foo=dropped")
    ap.add_argument("--unticked", nargs="*", default=[], metavar="ITEM",
                    help="(--log) checklist items that could not be ticked, with the reason")
    ap.add_argument("--repo", default=".", metavar="PATH", help="(--log) repository root")
    ap.add_argument("--annotation", metavar="FILE",
                    help="(--log) GFF the notebook read, e.g. genomic.refseq_select_mrna.gff")
    args = ap.parse_args()

    if args.log:
        if not (args.settings and args.promoters and args.genome_check):
            ap.error("--log needs --settings, --promoters and --genome-check")
        try:
            cfg = load(args.settings)
            p = write_run_log(cfg, Path(args.log) / "run_log.md", promoters=args.promoters,
                              genome_check=args.genome_check, repo=args.repo,
                              replaced=[r.replace("=", " → ") for r in args.replaced],
                              unticked=args.unticked, annotation=args.annotation)
        except (LockedSettingError, FileNotFoundError, ValueError) as e:
            print(f"{e}", file=sys.stderr)
            return 1
        print(f"wrote {p}")
        return 0

    if args.init:
        p = save_settings(copy.deepcopy(SETTABLE_DEFAULTS), args.init)
        print(f"wrote {p}")
        print("Edit the motifs, genes, p-value, upstream length and figure settings; everything else is fixed.")
        return 0

    try:
        cfg = load(args.check)
    except LockedSettingError as e:
        print(f"\nSetting not allowed\n\n  {e}\n", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"{e}", file=sys.stderr)
        return 1
    print(f"{args.check} is valid.")
    print(f"  motifs: {', '.join(cfg['analysis']['motifs'])}")
    print(f"  genes:  {len(cfg['analysis']['genes'])} requested")
    print(f"  pvalue: {cfg['analysis']['pvalue']:g}")
    print(f"  promoter: -{cfg['analysis']['promoter_upstream_bp']} / +{LOCKED['promoter_downstream_bp']} bp")
    return 0


if __name__ == "__main__":
    sys.exit(main())
