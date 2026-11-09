---
name: ft-motif-search-skill
description: Scan gene promoters for transcription factor binding motifs using RSAT matrix-scan with CIS-BP matrices, and produce a Quarto HTML report, a site map figure and a hits table packaged as a zip. Use this skill whenever the user wants to search for TF motifs or binding sites in promoters, scan promoters with a PWM or position weight matrix, run matrix-scan, look for Spic / Nfe2l2 / Bach1 (or other CIS-BP) motifs in a gene panel, regenerate or update the promoter motif report, or asks anything about the DNA_018 / DNA_032 promoter motif workflow — even if they only say "run the motif search", "scan these genes", or hand over a gene list and a repo.
model: sonnet
metadata:
  display-name: "FT Motif Search"
  version: "0.8.0"
  updated: "2026-11-07"
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
> The copy in the run directory is not the repository. What may be edited in it
> is set out under *Presentation changes the settings do not cover*, in the
> settings step below.
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
directory from last week, a cached `.ft` scan — none of it may be presented as
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

Once the check passes, build the RefSeq Select annotation, on every machine:

```bash
python scripts/prefilter_gff.py <gff path printed by check_genome.py>
```

It streams the full GFF and writes `genomic.refseq_select_mrna.gff` (~6 MB,
21,002 records) next to it — only the mRNA lines tagged `RefSeq Select`, the
records the notebook's `gtf_import` cell selects. The notebook reads that file
when it exists, so the parse takes under a second and ~0.1 GB of RAM instead
of ~1 minute and ~11 GB; a 3 GB sandbox is OOM-killed on the full file. This
is part of the method, not a deviation: the notebook still applies its own
filter, and the promoters, hits and coordinates were verified byte-identical
against a render from the full GFF. The file's header records the source GFF's
size and SHA-256; re-running is a no-op when it is current, and the notebook
refuses a file built from a different GFF. Do not hand-filter the GFF or patch
the notebook's GFF path instead — use this script.

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
python scripts/check_genes.py <genomic.refseq_select_mrna.gff> --genes Spic Nfe2l2 Hmox1 ...
```

This looks only at mRNA lines tagged `RefSeq Select` — the same filter the
analysis uses. Point it at the prefiltered file from step 1 and it answers
instantly; the full GFF gives the same answer, just slower.

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
| `2 kb (Recommended)` | 2,000 bp upstream + 200 bp downstream (2,201 bp) — the default window for this analysis | 2000 |
| `5 kb` | 5,000 bp upstream + 200 bp downstream (5,201 bp) | 5000 |

The user can type any other length through "Other" — a whole number of bp,
at least 1,000, with no upper limit; accept "3 kb" as 3000; anything under
1 kb is rejected. Set it as
`analysis.promoter_upstream_bp` through `runconfig.py` and relay its error if
rejected, then ask again. Do not refuse or second-guess a long window; for one
much longer than 5 kb, mention once that it will reach into neighbouring genes
and intergenic sequence, then run it as asked.

Only the upstream length is settable. The 200 bp downstream is locked: with
`-origin end` the TSS sits at `-(downstream + 1)`, so keeping downstream fixed
is what lets the upstream length change without shifting any coordinate. If
the user asks to change the downstream length, it is a locked setting (see
7b).

Say in the answer and the report which window was used, and flag it if it is
not 2 kb: the Markov background is estimated from the scanned promoters, so a
different window changes the background as well as the search space, and the
results are not directly comparable with the default 2 kb analysis.

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
├── notebook.ipynb                 # a COPY, outputs stripped, rendered here
├── notebook_report.html           # the rendered report (step 9)
├── promoters_sequences.fasta
├── motifs_coordinates_<name>.csv  # hits table
├── matrix_scan/
│   ├── scanmotif_<name>.ft        # raw RSAT output, ';' header intact
│   └── sitemap_<name>.{svg,png,pdf}
├── results_report/                # the notebook's copies; package_results.py dedupes
├── my_settings.yaml               # what the user chose (shareable)
├── run_config.yaml                # settable + locked values
├── run_log.md                     # what was run, changes from defaults, unticked items
└── results_<YYYYMMDD_HHMM>.zip    # built by package_results.py only (step 9)
```

These names are what the notebook writes when `DNA032_RESULTS` is set, and
they are the names `scripts/package_results.py` requires. Do not rename them.

**Always run the notebook copy with `DNA032_RESULTS` set to the run
directory.** Without it the notebook writes to the repository's `Results/`,
which both modifies tracked files and leaves the run directory without the
files the zip needs.

Use `runs/` at the repository root with `runs/` in `.gitignore`, or a path
outside the repository entirely. The timestamp is what makes "never reuse a
previous result" checkable: two runs can never collide, and nothing from last
week can be mistaken for today's output.

Extract promoters into the run directory — do not reuse a committed promoter
FASTA when the genome is available (see the input/output rule above).

Extract promoters with the window chosen in step 5 (`promoter_upstream_bp`
upstream, 200 bp downstream of the TSS; in the notebook copy set
`PROMOTER_UPSTREAM_BP` and leave `PROMOTER_DOWNSTREAM_BP` and `TSS_OFFSET`
alone), then scan. Report progress at each stage — silence reads as a hang. Check
that the rendered report's summary says the annotation was read from
`genomic.refseq_select_mrna.gff`; if it names `genomic.gff`, step 1's
prefilter was skipped (the result is the same, but the full parse needs
~11 GB of RAM).

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

The notebook saves the site map as SVG, PNG and PDF under
`matrix_scan/` in the run directory; do not redraw it separately.

**Execute the notebook copy with `quarto render`, once, and with nothing
else.** `DNA032_PROJECT` is the repository root; the notebook needs it when the
run directory is outside the clone, or it falls back to a path on the
maintainer's server.

```bash
cd runs/<YYYYMMDD_HHMM>
DNA032_RESULTS="$PWD" DNA032_PROJECT="<repository root>" QUARTO_PYTHON="$(command -v python3)" \
    quarto render notebook.ipynb --to html --execute --output notebook_report.html
```

Never execute the copy with nbclient, papermill or `jupyter nbconvert
--execute`. The notebook's last cell (`render_report`) is marked `eval: false`,
which only Quarto honours; any other executor runs it. That cell finds the
notebook by its long file name, and the copy is called `notebook.ipynb`, so it
resolves the **committed** notebook and renders that: it re-runs the default
panel (37 genes, 5 kb) over the run's outputs and modifies a tracked file. This
happened in a test run. One `quarto render` also runs the analysis once;
executing first and rendering afterwards runs it twice.

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

**Presentation changes the settings do not cover.** The boundary is **analysis
versus presentation**.

*The analysis is never touched.* That is where a motif lies in the promoter —
the site positions, strands, scores and p-values, which are the result itself —
and everything that produces them: the promoter extraction, the matrix
conversion, the RSAT calls and every parameter in them, and the hit table. It
also includes what marker size means: size must keep growing with significance
(a smaller p-value gives a larger marker), and that mapping is not changed. A
request to move a site or change what marker size means is refused exactly
like a locked analysis setting, and recorded the same way: in
`requested_changes.md`'s "Refused or not possible" section, naming which of
the two it would have touched.

*Everything else visual may be changed*, including scaling. That covers marker
shape, colour, font weight and size, labels, title, legend, figure size and
layout, the order of the promoter lanes, and making all markers or all text
larger or smaller together. The settings above expose only some of these, and
the notebook does not read all of the ones they expose.

**Use `scripts/restyle_sitemap.py` first, on the already-rendered
`sitemap_*.svg`.** It recolours a motif, hides a gene's lane, edits the title
or a label's text, sets font-weight or font-size, and swaps a marker's shape —
each new shape sized from that marker's own existing bounding box, so a point
that was bigger because it was more significant stays exactly as big. It never
writes a coordinate or a `transform`, checks that invariant itself before
writing anything, and refuses (with nothing written) if a requested gene or
motif cannot be found. Run it on the SVG in the run directory:

```bash
python scripts/restyle_sitemap.py runs/<YYYYMMDD_HHMM>/matrix_scan/sitemap_<name>.svg \
    --recolor Spic=#1B9E77 --hide-gene Sqstm1 --set-text title="Nrf2 network" --bold title \
    --log runs/<YYYYMMDD_HHMM>/requested_changes.md
```

It regenerates `sitemap_<name>.png` and `sitemap_<name>.pdf` from the edited
SVG (via `cairosvg`) so the three formats in the zip agree; if `cairosvg` is
not installed it says so and leaves the PNG/PDF as they were — tell the user
only the SVG changed rather than shipping formats that disagree. For a visual
change it does not support (figure size, layout, promoter sort order, a new
kind of element), edit the **figure-drawing code of the notebook copy in the
run directory** instead, then run that copy again with `quarto render`, as in
step 7, so the figure and the report still come from the same notebook. The
repository stays untouched either way. Do not redraw a figure outside the
notebook or `restyle_sitemap.py`, and do not edit an output by hand.

With `--log`, `restyle_sitemap.py` writes its own entry into
`requested_changes.md` (see below) from what it actually changed — do not
also describe the same edit yourself.

For a change applied by editing the notebook copy instead, there is no
equivalent self-check — the figure-drawing code can do anything, and nothing
here tries to constrain what. What keeps the boundary real is narrower and
simpler: the edit stays inside the figure-drawing cell, never touches the
analysis cells (where `hits`, `lim`, `tss_pos` or anything upstream of them is
computed), and the record of it in `requested_changes.md` is **the new cell's
actual code**, pasted in full as a fenced code block, not a prose description
of it. That makes the entry something a reader can check for themselves —
nothing in it computes a position — rather than something they have to take on
trust. Name the cell or function changed, alongside the code.

If a requested change would remove information the figure carries, say so once
and offer a way to keep it. Circles instead of triangles, for example, drop the
strand that the triangles show by pointing up or down; filled and open circles,
or an added strand column, would keep it. Then do what the user decides.

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
Nothing writes it on its own — call `runconfig.py` explicitly:

```bash
python scripts/runconfig.py --write-config runs/<YYYYMMDD_HHMM> \
    --settings runs/<YYYYMMDD_HHMM>/my_settings.yaml
```

`verify_run.py` and `package_results.py` both require `run_config.yaml`; skip
this call and the run cannot be packaged.

Finally, write `run_log.md` — what was run, what differs from the defaults, and
anything that went wrong. Write it on **every** run, not only when something
changed: a missing log must never be read as "no changes".

```bash
python scripts/runconfig.py --log runs/<YYYYMMDD_HHMM> \
    --settings runs/<YYYYMMDD_HHMM>/my_settings.yaml \
    --repo <repository root> \
    --promoters re-extracted \
    --genome-check passed \
    --annotation genomic.refseq_select_mrna.gff \
    --replaced Nrf2=Nfe2l2 Foo=dropped \
    --unticked "<item> — <reason>"
```

`--promoters` is `re-extracted` or `reused:<path to the FASTA scanned>`;
`--genome-check` is `passed` or `not available`; `--annotation` is the file
the report's summary says was read; `--replaced` lists the gene
check outcomes (`OLD=NEW`, or `OLD=dropped`); `--unticked` lists checklist items
that could not be ticked. Omit the last two when there are none.

Do not write the "changes from defaults" part yourself — `runconfig.py`
computes it against `SETTABLE_DEFAULTS` so the list is the same every time.
Write the log after walking the checklist at the end of this file, so
`--unticked` reflects it; if the run stops early, still write the log with
what was done and why it stopped.

Also write `requested_changes.md` — a register of anything the user asked for
beyond the four questions, in their own words, whether it was applied, refused,
not possible here, or needs the maintainer. Write it on **every** run, even
when nothing was asked (it then says so); a missing file must never be read as
"nothing was requested". Its "Applied" entries, for a visual change made with
`restyle_sitemap.py --log`, are written by that script itself from what it
actually changed — do not duplicate them by hand. Add everything else yourself,
one entry per request:

```markdown
## Refused or not possible
- "<what the user asked>" → <reason>. Locked: <setting>. Contact sara.salazar@gimm.pt.

## For the maintainer
- "<what the user asked>" → needs a code or method change, not a setting
```

For a refusal, give the setting's name and relay the message from
`runconfig.py` as it was shown. Do not log the answers to the four questions —
`my_settings.yaml` and `run_config.yaml` already hold those — and do not log
your own suggestions as the user's requests; if you suggested something and
the user accepted it, record it as *suggested by the agent, accepted*.

### 8. Show the site map, then ask about the zip (option box) — then stop

Return the site map image (the PNG) to the user, displayed in the chat, with
a short summary underneath: motifs scanned, number of promoters, number of
sites per motif, the promoter window, the p-value, and any genes with no
site. Also hand back the site map **SVG and PDF** as files the user can
download — neither displays inline, so the PNG is what they see and the SVG
and PDF are what they keep.

Then ask one single-select question: *"Do you want the zip with the full HTML
report?"*

| Option label | Description to show |
|---|---|
| `Yes, build the zip` | Package the HTML report with the site map, hits table, raw scan output and run record |
| `No, the image is enough` | Stop here; the run files stay in the run directory |

### 9. Package (only if the user said yes)

The report was built in step 7 by the same `quarto render`; do not render again.
Build the zip with `package_results.py`:

```bash
python <skill>/scripts/package_results.py runs/<YYYYMMDD_HHMM>
```

Before it zips anything, `package_results.py` runs `verify_run.py`, which
compares what the run produced with what the run's own `run_config.yaml` says
was asked for (the genes, the window, the p-value, the motifs) and checks the
repository was left unchanged. A failure there means the run is wrong even
though every file is present: do not zip it anyway. Show its lines in the reply.

**Build the zip only with `package_results.py`.** It holds the contract — the
list of files every zip must contain — as code, and refuses to build a zip
that is missing any of them, naming what is absent. If it refuses, produce the
missing files and run it again. Never assemble a zip by hand, never zip a
directory yourself, and never describe a partial zip as complete. The
notebook does not package; any zip it left in `Results/` is not the
deliverable.

`--allow-missing <pattern>` exists for a file that legitimately cannot be
produced in this run. Use it only after telling the user which file and why;
the script prints every waived file, and that output goes in the reply.

Show the user the script's `OK` output — the zip path and the file list — so
they can see what the zip holds. The raw `.ft` file keeps its `;` header: that
header is the authoritative record of the background model and pseudo-counts,
and `pd.read_csv(..., comment=";")` discards it.

If the user said no, do not package. The report stays in the run directory with
the other files; tell them where it is, and that they can ask for the zip later
from the same run.

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

**Never put the RSAT environment on `PATH`.** It ships its own `python3`, which
has none of the packages installed into the system Python (`pyfaidx`,
`biopython`, `pyranges`, the Jupyter stack Quarto needs) and silently shadows
it. Do not `micromamba activate rsat`; use `RSAT_ENV`. `motifscan.RSAT` and the
notebook build a private `PATH` for the RSAT subprocesses only. Call
`python3 -m pip` and `python3 …`, not bare `pip` or `python`.

**If the repository changed during a run, do not repair it with git.**
`checkout`, `restore`, `reset`, `stash` and `clean` are forbidden. In a sandbox
the clone is disposable: discard it, clone again, and redo the run. On a user's
machine, tell them which tracked files changed and let them restore them.

## Files

- `scripts/fetch_genome.sh` — download the genome from the GitHub Release
- `scripts/check_genome.py` — genome completeness gate
- `scripts/check_genes.py` — fast RefSeq Select lookup, UniProt links for misses
- `scripts/motifscan.py` — matrices, background, scan; importable or CLI
- `scripts/runconfig.py` — settable vs locked settings; load, validate, save; write `run_config.yaml` and `run_log.md`
- `scripts/restyle_sitemap.py` — presentation-only edits to a rendered site map SVG (colour, hidden gene, text, font, marker shape); never touches a position; `--log` writes to `requested_changes.md`
- `scripts/package_results.py` — the results contract; builds the zip or refuses and names what is missing

## Checklist before finishing

Walk this before reporting back. It is an instruction, not documentation: check
each item against what actually happened in this session.

**Any item that cannot be ticked must be reported to the user**, naming which
one and why. An unticked box nobody is told about is the failure this checklist
exists to prevent — silence reads as success.

This skill owns the analysis. When it is run through `motif-scan-from-github`,
that skill's checklist covers the clone and the environment; walk both.

- [ ] `check_genome.py` passed before anything was extracted or scanned — or, if no genome was available, that was said before the run started
- [ ] `prefilter_gff.py` run after the genome check, and the report's summary names `genomic.refseq_select_mrna.gff` as the annotation read — no hand-filtered GFF and no edit to the notebook's GFF path
- [ ] Motifs chosen by the user (step 3), not assumed from a previous run or the examples in this file
- [ ] Gene symbols given by the user (step 4), `check_genes.py` run on them, and every miss resolved by the user — replaced or dropped explicitly, never silently skipped
- [ ] Promoter length chosen by the user (step 5) and that exact window used for extraction
- [ ] p-value chosen by the user (step 6) and that exact value passed to the scan
- [ ] Promoters handled by the input/output rule: **genome available** → re-extracted into the run directory, committed FASTA ignored; **genome unavailable** → committed FASTA checked (every requested gene present, every sequence upstream + 201 bp for the chosen window) and its reuse disclosed in the answer and in the report
- [ ] Notebook copied into the run directory with stored outputs stripped, rendered with `--execute`; the committed notebook was never rendered in place
- [ ] Notebook copy executed once, by `quarto render` only — never nbclient, papermill or nbconvert — with the system `python3`, and the RSAT environment never on `PATH`
- [ ] No locked setting changed or worked around; any request for one was refused with the `runconfig.py` message
- [ ] Any visual change was made with `restyle_sitemap.py` where it could handle it, or otherwise only in the figure-drawing code of the notebook copy in the run directory — never in the repository, never in the analysis cells — with no site position changed and the size-to-significance mapping intact; for a notebook-copy edit, the new cell's actual code (not a description of it) is in `requested_changes.md`
- [ ] All outputs written to `runs/<YYYYMMDD_HHMM>/` (or a path outside the repository); `git status` shows the repository unchanged
- [ ] `my_settings.yaml` and `run_config.yaml` written to the run directory, and the user told where they are
- [ ] `run_log.md` written by `runconfig.py --log` (not by hand), with the true promoter source, genome check result, gene replacements and every unticked item from this list
- [ ] `requested_changes.md` written on every run (even if empty of requests): `restyle_sitemap.py --log` entries for any visual change it applied, and every other out-of-scope request added by hand with its outcome — applied, refused (naming the locked setting), not possible here, or needs the maintainer
- [ ] Site map PNG shown in the chat with its summary, and the site map SVG and PDF handed back as files (step 8), before any packaging
- [ ] Notebook copy run with `DNA032_RESULTS` set to the run directory, so nothing was written to the repository's `Results/`
- [ ] `verify_run.py` passed (it runs inside `package_results.py`) or its failures were reported; if the repository changed, the run was discarded and redone from a fresh clone, not repaired with git
- [ ] Zip built only after the user answered yes (step 9), only by `package_results.py`, and its `OK` output (zip path and file list, plus any waived file) shown in the reply
