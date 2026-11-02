---
name: ft-motif-search-skill
description: Scan gene promoters for transcription factor binding motifs using RSAT matrix-scan with CIS-BP matrices, and produce a Quarto HTML report, a site map figure and a hits table packaged as a zip. Use this skill whenever the user wants to search for TF motifs or binding sites in promoters, scan promoters with a PWM or position weight matrix, run matrix-scan, look for Spic / Nfe2l2 / Bach1 (or other CIS-BP) motifs in a gene panel, regenerate or update the promoter motif report, or asks anything about the DNA_018 / DNA_032 promoter motif workflow — even if they only say "run the motif search", "scan these genes", or hand over a gene list and a repo.
metadata:
  display-name: "FT Motif Search"
  version: "0.2.0"
  updated: "2026-11-02"
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
> `.claude/skills/ft-motif-search-skill/` is the only one. Claude Code loads it
> from the repository root, and a sandbox uses it from a fresh clone of the
> GitHub repository, so there is no separate installed copy to keep in sync.

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
  length (upstream + 201 bp: 2201 bp for the default 2 kb window), and that it
  was extracted with the window the user chose; if any check fails, stop and say
  the promoters must be extracted instead.

**Never run against a partial genome.** A truncated FASTA still produces
promoters — shorter ones, or none for genes on the missing contigs — and the
scan succeeds without complaint. Run `check_genome.py` first and refuse if it
fails.

## Workflow

Follow these in order. Steps 3, 4, 5, 6 and 8 are conversation gates: ask,
stop, and wait for the user's answer before going on. Ask one question at a
time, in this order: motifs, genes, promoter length, p-value, then (after
showing the site map) the zip.

**Ask with an option box whenever the answer is a choice.** Use the client's
multiple-choice question tool (`AskUserQuestion` in Claude Code, or the
equivalent ask-user / input tool in claude.ai). Only fall back to a plain
numbered list in the message if no such tool is available. Gene symbols are
free text, so ask for those in a normal message.

Steps 1 and 2 need no input; do them first, quietly, and only report if they
fail, so the user is not asked for choices that cannot then be run.

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

If the genome is absent, first confirm the Python environment can read the
compressed files, so a missing package surfaces before the ~0.9 GB download
rather than at promoter extraction:

```bash
python -c "import pyranges, pyfaidx, Bio"   # Bio = biopython, needed for bgzipped FASTA
```

Install whatever is missing (`pip install "pyranges<1" pyfaidx biopython`),
then fetch it from the repo's GitHub Release:

```bash
bash scripts/fetch_genome.sh <refseq_dir>
```

This works from sandboxes that cannot reach NCBI. It downloads the bgzipped
FASTA with its `.gzi` and `.fai` indexes and the gzipped GFF (~0.9 GB),
verifies them against the release's `SHA256SUMS`, and **leaves them
compressed** — unpacking needs ~3.7 GB, more than a sandbox usually has free.
Do not decompress them yourself: everything downstream reads the `.gz` files
directly (pyfaidx/pyranges for the FASTA and GFF, `check_genes.py` for the
GFF), and a disk that fills mid-unpack leaves a truncated genome behind.
`check_genome.py` recognises this layout and verifies the SHA-256 sums in
place of the uncompressed sizes; use the `fasta` and `gff` paths it prints,
which then point at the `.gz` files. Plain files, where they exist, are
preferred and checked by size as before. If GitHub release downloads
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

### 3. Ask which motifs (option box, multi-select) — then stop

Offer the curated set, which have logos bundled in the CIS-BP folder, as one
multi-select question with exactly these four options:

| Option label | Description to show | CIS-BP accession |
|---|---|---|
| `Spic` | Spic | M03221_3.10 |
| `Nfe2l2_1` | Nfe2l2, first matrix | M09222_3.10 |
| `Nfe2l2_2` | Nfe2l2, second matrix | M10174_3.10 |
| `Bach1` | Bach1 | M10181_3.10 |

Put the accession in each option's description so the choice is recorded
unambiguously. Question: *"Which transcription factor motifs should I scan
for? (choose one or more)"*.

One or several. Do not pre-select, mark one as recommended, or silently
default to all four — which motifs are scanned is a scientific choice that
belongs to the user. If they answer with "Other" and name a different CIS-BP
motif, say it is outside the curated set (no bundled logo) and confirm before
using it.

### 4. Ask for the gene symbols, check them, and stop again

Ask in a plain message: *"Which gene symbols should I scan? (mouse symbols,
e.g. Hmox1, Gclm, Nqo1)"*. Take the gene symbols, then:

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

### 5. Ask for the promoter length (option box) — then stop

One single-select question: *"How far upstream of the TSS should the promoter
region extend?"*, with these options, in this order:

| Option label | Description to show | `promoter_upstream_bp` |
|---|---|---|
| `1 kb` | 1,000 bp upstream + 200 bp downstream (1,201 bp) | 1000 |
| `2 kb (Recommended)` | 2,000 bp upstream + 200 bp downstream (2,201 bp); published method default | 2000 |
| `5 kb` | 5,000 bp upstream + 200 bp downstream (5,201 bp) | 5000 |

The user can type another length through "Other" (a whole number of bp,
1,000–10,000; accept "3 kb" as 3000; anything under 1 kb is rejected). Set it as `analysis.promoter_upstream_bp`
through `runconfig.py` and relay its error if rejected, then ask again.

Only the upstream length is settable. The 200 bp downstream is locked: with
`-origin end` the TSS sits at `-(downstream + 1)`, so keeping downstream fixed
is what lets the upstream length change without shifting any coordinate. If
the user asks to change the downstream length, it is a locked setting (see
6b).

Say in the answer and the report which window was used, and flag it if it is
not 2 kb: the Markov background is estimated from the scanned promoters, so a
different window changes the background as well as the search space, and the
results are not directly comparable with the published analysis.

### 6. Ask for the p-value (option box) — then stop

One single-select question: *"Which p-value threshold should matrix-scan
use?"*, with these options, in this order:

| Option label | Description to show |
|---|---|
| `1e-4 (Recommended)` | Published method default |
| `1e-3` | More permissive: more sites, more false positives |
| `1e-5` | Stricter: fewer, higher-confidence sites |

The user can type any other value through "Other". The p-value is settable,
but it must be a number in (0, 0.1]; set it through `runconfig.py` and relay
its error if the value is rejected, then ask again. Say in the answer and the
report which threshold was used, and flag it if it is not 1e-4, since results
at another threshold are not directly comparable with the published analysis.

### 7. Run

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

Extract promoters with the window chosen in step 5 (`promoter_upstream_bp`
upstream, 200 bp downstream of the TSS; in the notebook copy set
`PROMOTER_UPSTREAM_BP` and leave `PROMOTER_DOWNSTREAM_BP` and `TSS_OFFSET`
alone), then scan. Report progress at each stage — the GFF parse alone takes a
couple of minutes and silence reads as a hang.

```python
from motifscan import RSAT, cisbp_to_transfac, matrix_scan
cisbp_to_transfac(cisbp_dir, {"M03221_3.10": "Spic", ...}, out/"matrices.tf")
hits = matrix_scan(promoter_fasta, out/"matrices.tf", ["Spic", "Bach1"],
                   out/"scan.ft", genes=panel)
```

Pass the p-value chosen in step 6. The other scan parameters are fixed by the
published method: order-1 Markov background estimated from the input
promoters, pseudo-count 1, background pseudo-frequency 0.01, both strands,
`-origin end`.

Then draw the site map (SVG and PNG) into the run directory.

### 7b. Settings: what the user may change

`scripts/runconfig.py` holds the boundary. **Do not implement it by judgement
— load the config through that module and let it decide**, so the same answer
comes back every time.

Settable: which transcription factors, which genes, the p-value, the
upstream promoter length, and everything about the figures (motif colours, width, row height, dpi, output
formats, title, sort order, font size, legend) and the zip contents.

Locked: the reference genome (species, accession, assembly, annotation
release), background model and Markov order, pseudo-counts, strand handling,
coordinate origin, downstream promoter length, transcript filter, matrix scaling, gene
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

### 8. Show the site map, then ask about the zip (option box) — then stop

Return the site map image (the PNG) to the user, displayed in the chat, with
a short summary underneath: motifs scanned, number of promoters, number of
sites per motif, the promoter window, the p-value, and any genes with no
site.

Then ask one single-select question: *"Do you want the zip with the full HTML
report?"*

| Option label | Description to show |
|---|---|
| `Yes, build the zip` | Render the HTML report and package it with the site map, hits table and raw scan output |
| `No, the image is enough` | Stop here; the run files stay in the run directory |

### 9. Package (only if the user said yes)

Render the notebook copy and deliver a zip containing the HTML report, the
site map as **both SVG and PNG**, the hits CSV, and the raw `.ft.txt` with its
`;` header intact — that header is the authoritative record of the background
model and pseudo-counts, and `pd.read_csv(..., comment=";")` discards it.

If the user said no, do not render the report. Tell them where the run
directory is, and that they can ask for the zip later from the same run.

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
sequence end, so the TSS sits at `-(downstream_bp + 1)`. Changing the
downstream length without changing the offset silently shifts every reported
coordinate; that is why downstream is locked. The upstream length is free to
change: it only moves where the sequence starts, not where the TSS sits.

## Files

- `scripts/fetch_genome.sh` — download the genome from the GitHub Release
- `scripts/check_genome.py` — genome completeness gate
- `scripts/check_genes.py` — fast RefSeq Select lookup, UniProt links for misses
- `scripts/motifscan.py` — matrices, background, scan; importable or CLI
- `scripts/runconfig.py` — settable vs locked settings; load, validate, save
