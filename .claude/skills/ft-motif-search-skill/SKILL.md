---
name: ft-motif-search-skill
description: Scan gene promoters for transcription factor binding motifs using RSAT matrix-scan with CIS-BP matrices, and produce a Quarto HTML report, a site map figure and a hits table packaged as a zip. Use this skill whenever the user wants to search for TF motifs or binding sites in promoters, scan promoters with a PWM or position weight matrix, run matrix-scan, look for Spic / Nfe2l2 / Bach1 (or other CIS-BP) motifs in a gene panel, regenerate or update the promoter motif report, or asks anything about the DNA_018 / DNA_032 promoter motif workflow — even if they only say "run the motif search", "scan these genes", or hand over a gene list and a repo.
metadata:
  display-name: "FT Motif Search"
  version: "0.1.0"
  updated: "2026-10-29"
  canonical: ".claude/skills/ft-motif-search-skill/ in the DNA_032 repository"
---

# FT Motif Search — promoter scan for transcription factor motifs

Extract promoter sequences for a panel of genes, scan them for transcription
factor motifs with RSAT matrix-scan, and package a report.

> **Never modify the repository.** Treat every tracked file — the notebook,
> the scripts, this skill, the CIS-BP matrices — as read-only input. A run
> writes only to its own output directory and touches nothing else. Do not run
> `git add`, `commit`, `push`, `checkout`, `stash`, `reset` or `clean`, and do
> not edit a tracked file even when asked to fix something: propose the change
> as a diff and let the user apply it. The repository is the record of a
> published method; a run must leave it byte-for-byte unchanged.
>
> In particular, never render the notebook in place. Copy it into the run
> directory first and render the copy, or the stored outputs of the committed
> notebook are destroyed.
>
> **This skill lives in the repository.** The copy under
> `.claude/skills/ft-motif-search-skill/` is canonical. Any copy installed in a
> Claude profile is a build output, regenerated with `./package_skill.sh`.

The analysis is driven by a Quarto notebook. This skill parameterises that
notebook, gates it on checks that are easy to skip and expensive to get wrong,
and hands back a zip.

## Two rules that override convenience

**Never reuse a previous result.** Stored notebook outputs, a `Results/`
directory from last week, a cached `.ft.txt` — none of it may be presented as
the output of this run. Strip stored outputs before rendering, render with
`--execute`, and write to a timestamped directory. If something cannot be
recomputed, say so plainly instead of serving the old artefact. Rendering a
notebook with `--no-execute` reformats someone else's run; that is exactly what
this rule forbids.

The rule separates inputs from outputs. The genome, the GFF and the CIS-BP
matrices are inputs: read them freely. The scan, the site map, the hits table
and the report are outputs: they must come from this run, always.

A committed promoter FASTA such as `Results/promoters_sequences.fasta` sits
between the two — it is a previous run's output being offered as an input — so
it has its own rule:

- **Genome available: always re-extract.** Ignore the committed FASTA
  completely, even when the requested genes all appear in it and re-extraction
  costs minutes. This is the normal case on a machine with the reference.
- **Genome unavailable: scanning it is permitted, with disclosure.** Say
  plainly, in the answer and in the report, that the promoters come from a
  previous extraction and were not regenerated in this run. First confirm it
  actually contains every requested gene and that each sequence is the expected
  length (2201 bp for the default window); if either check fails, stop and say
  the promoters must be extracted instead.

**Never run against a partial genome.** A truncated FASTA still produces
promoters — shorter ones, or none for genes on the missing contigs — and the
scan succeeds without complaint. Run `check_genome.py` first and refuse if it
fails.

## Workflow

Follow these in order. Steps 3 and 4 are conversation gates: stop and wait for
the user.

### 1. Locate the project and verify the genome

Find the RefSeq directory (default `Data/ncbi_dataset_RefSeq_*`) and run:

```bash
python scripts/check_genome.py <refseq_dir> \
    --expect-annotation GCF_000001635.27-RS_2024_02
```

The expected accession, assembly and annotation release are locked values in
`runconfig.py`; take them from there rather than retyping them, so the gate
and the run record can never disagree.

It compares each file against the uncompressed sizes recorded in NCBI's own
`dataset_catalog.json` and reports the annotation release. The JSON it prints
carries `fasta` and `gff` paths — use those downstream rather than guessing.

If the genome is absent, fetch it from the repo's GitHub Release (bgzipped
copies, checksum-verified and decompressed in place):

```bash
bash scripts/fetch_genome.sh <refseq_dir>
```

This works from sandboxes that cannot reach NCBI. If GitHub release downloads
are also blocked, do not improvise a substitute; tell the user to fetch it
from NCBI instead:

```bash
datasets download genome accession GCF_000001635.27 --include genome,gff3
```

Either way, run `check_genome.py` afterwards. The genome is deliberately not
in the repo: GitHub rejects files over 100 MB and these are 2.7 GB and
920 MB. A clone will not have them.

### 2. Check RSAT

`motifscan.RSAT()` discovers an environment from `$RSAT_ENV`, `PATH`, or the
usual conda env directories. If none exists:

```bash
conda create -n rsat -c bioconda -c conda-forge rsat-core
```

bioconda ships `rsat-core` for linux-64, linux-aarch64 and osx-64 but **not
osx-arm64**. On Apple Silicon use `CONDA_SUBDIR=osx-64` or a container, and
say so rather than letting the install fail opaquely.

### 3. Ask which motifs — then stop

Offer the curated set, which have logos bundled in the CIS-BP folder:

| Label | CIS-BP accession | TF |
|---|---|---|
| `Spic` | M03221_3.10 | Spic |
| `Nfe2l2_1` | M09222_3.10 | Nfe2l2 |
| `Nfe2l2_2` | M10174_3.10 | Nfe2l2 (second matrix) |
| `Bach1` | M10181_3.10 | Bach1 |

One or several. Do not pick for the user, and do not silently default to all
four — which motifs are scanned is a scientific choice that belongs to them.

### 4. Ask for the gene panel, check it, and stop again

Take the gene symbols, then:

```bash
python scripts/check_genes.py <genomic.gff> --genes Spic Nfe2l2 Hmox1 ...
```

This streams the GFF looking only at mRNA lines tagged `RefSeq Select` — the
same filter the analysis uses — and answers in seconds rather than the minutes
a full `pyranges` parse costs.

**If any symbol is missing**, stop. Report which ones, give the UniProt link
the script generates for each (symbols change; the alternative name is usually
one click away), and ask for replacements. Re-check the new names. Repeat until
the user is satisfied, then proceed with the genes that resolved — never drop a
missing gene silently, and never proceed without asking.

If a symbol has more than one RefSeq Select transcript, mention it and keep all
of them. That matches the established analysis; the point is that the promoter
count is explained rather than surprising.

### 5. Run

Create a run directory **outside the repository's tracked files** and write
everything there:

```
runs/<YYYYMMDD_HHMM>/
├── notebook.ipynb        # a COPY, outputs stripped, rendered here
├── promoters.fasta
├── scan.ft.txt
└── report/
```

Use `runs/` at the repository root with `runs/` in `.gitignore`, or a path
outside the repository entirely. The timestamp is what makes "never reuse a
previous result" checkable: two runs can never collide, and nothing from last
week can be mistaken for today's output.

Extract promoters into the run directory — do not reuse a committed promoter
FASTA when the genome is available (see the input/output rule above).

Extract promoters (default window: 2000 bp upstream, 200 bp downstream of the
TSS), then scan. Report progress at each stage — the GFF parse alone takes a
couple of minutes and silence reads as a hang.

```python
from motifscan import RSAT, cisbp_to_transfac, matrix_scan
cisbp_to_transfac(cisbp_dir, {"M03221_3.10": "Spic", ...}, out/"matrices.tf")
hits = matrix_scan(promoter_fasta, out/"matrices.tf", ["Spic", "Bach1"],
                   out/"scan.ft", genes=panel)
```

Scan parameters are fixed by the published method and should not be changed
without the user saying so: order-1 Markov background estimated from the input
promoters, pseudo-count 1, background pseudo-frequency 0.01, both strands,
p <= 1e-4, `-origin end`.

### 5b. Settings: what the user may change

`scripts/runconfig.py` holds the boundary. **Do not implement it by judgement
— load the config through that module and let it decide**, so the same answer
comes back every time.

Settable: which transcription factors, which genes, the p-value, and
everything about the figures (motif colours, width, row height, dpi, output
formats, title, sort order, font size, legend) and the zip contents.

Locked: the reference genome (species, accession, assembly, annotation
release), background model and Markov order, pseudo-counts, strand handling,
coordinate origin, promoter window, transcript filter, matrix scaling, gene
matching. These define the method — altering one produces results that look
valid but are not comparable with previous runs or the published analysis.

If a user asks for a locked change, do not do it and do not work around it by
editing the scripts. Explain which setting it is and why it is fixed, then
point them at **sara.salazar@gimm.pt** to discuss it. `runconfig.py` raises
with that message already; relay it rather than inventing your own.

Requests that sound like analysis but are actually presentation — "make the
Spic markers bigger", "sort the promoters alphabetically", "I want it as a
PDF" — are all allowed. When unsure which side something falls on, check
whether it would change the sites reported. If it would, it is locked.

Save what the user chose so they can reuse and share it:

```bash
python scripts/runconfig.py --init my_settings.yaml   # starter file
python scripts/runconfig.py --check my_settings.yaml  # validate
```

Write their settings to `my_settings.yaml` in the run directory and tell them
it is there. That file contains only the settable part, so handing it to a
colleague reproduces their run without carrying hidden method differences.
Every run also writes `run_config.yaml` with the settable **and** locked
values together, so the report always records the parameters that produced it.

### 6. Package

Deliver a zip containing the HTML report, the site map as **both SVG and PNG**,
the hits CSV, and the raw `.ft.txt` with its `;` header intact — that header is
the authoritative record of the background model and pseudo-counts, and
`pd.read_csv(..., comment=";")` discards it. Also hand the user the site map
image on its own, outside the zip.

## Things that will bite

**`-bginput` is broken.** matrix-scan's built-in background estimation fails
with "the sum must be strictly positive" and then divides by zero in
`RSAT/matrix.pm`. Confirmed in bioconda rsat-core 2025.04.04 and still present
in 2026.10.08 — permanent, not a patch awaiting a fix. `motifscan.py` estimates
the background with `oligo-analysis` and passes it via `-bgfile`: same
estimator, same sequences, made explicit.

**matrix-scan can fail while exiting 0**, printing `Error` to stdout. Checking
the return code alone is not enough; `RSAT.__call__` greps for it. Do not
simplify that away.

**There is no `matrix-scan` on PATH.** rsat-core dispatches through a single
`rsat` entry point. The `matrix-scan-quick` binary that *is* on PATH is a
different program. The env's `bin` must lead `PATH` or the Perl shebang picks
the system interpreter and the tool dies on missing modules.

**Gene matching is exact, deliberately.** The original notebook selected
promoters with `any(g.lower() in header.lower() for g in genes)`, which is safe
only because an earlier exact filter had already narrowed the FASTA to the
requested panel. Given an arbitrary gene list it would pull `Cat1` in alongside
`Cat` with nothing in the output to reveal it. `select_promoters()` matches the
gene field exactly and raises on any requested gene that finds no promoter.

**`-origin end` couples to `TSS_OFFSET`.** Positions are negative from the
sequence end, so the TSS sits at `-(downstream_bp + 1)`. Changing the promoter
window without changing the offset silently shifts every reported coordinate.

## Files

- `scripts/check_genome.py` — genome completeness gate
- `scripts/check_genes.py` — fast RefSeq Select lookup, UniProt links for misses
- `scripts/motifscan.py` — matrices, background, scan; importable or CLI
- `scripts/runconfig.py` — settable vs locked settings; load, validate, save
