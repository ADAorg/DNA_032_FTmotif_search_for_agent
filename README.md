# DNA_032 – Transcription-factor motif search in mouse promoters

Scans the promoters of a gene panel (the *Spic* / Nfe2l2 / ferroptosis network) for binding sites of
SpiC, Nfe2l2 (two matrices) and Bach1, and produces a site map and a coordinate table.

The analysis can be run two ways: directly through the notebook, or through the **Claude agent** bundled
with this repository, which asks which motifs and genes you want, checks the gene symbols against the
annotation before running, and packages the report. See [The Claude agent](#the-claude-agent).

**What the notebook does**

1. Reads the RefSeq GRCm39 annotation and keeps the **RefSeq Select** (canonical) transcript of each gene.
2. Builds strand-aware promoter windows (default **−2000 / +200 bp** around the TSS; the upstream length can be changed) and extracts them from the genome.
3. Loads the CIS-BP PWMs for the TFs, converts them to TRANSFAC format.
4. Scans the promoters with RSAT `matrix-scan` (P < 1e-4, order-1 Markov background estimated from the scanned promoters).
5. Draws the site map, converts hits to genomic coordinates, and renders/zips an HTML report.

Everything is in one notebook: [Notebooks/PromoterExtraction_adapted_with_rsatconda_refseqannotation.ipynb](Notebooks/PromoterExtraction_adapted_with_rsatconda_refseqannotation.ipynb)
(Quarto-annotated Jupyter notebook).

## Project structure

```
DNA_032_FTmotif_search_for_agent/
├── .claude/
│   └── skills/
│       └── ft-motif-search-skill/              # the Claude agent (canonical copy)
│           ├── SKILL.md
│           └── scripts/                        # fetch_genome, check_genome, check_genes, motifscan, runconfig
├── Data/
│   ├── ncbi_dataset_RefSeq_GCF_000001635.27/   # genome FASTA + GFF3 annotation (not in git, see below)
│   └── Mus_musculus_<date>_CISBP/              # CIS-BP download: pwms_all_motifs/, logos_used_motifs/
├── Notebooks/                                  # the analysis notebook
├── Results/                                    # notebook outputs
│   ├── promoters_sequences.fasta               # extracted promoters (regenerated on every run)
│   ├── motifs_coordinates_SpiC_network_all_TFs.csv
│   ├── matrix_scan/                            # RSAT inputs/outputs: .tf matrices, .ft scan, sitemap/logo SVGs, sitemap PDF
│   └── results_report/                         # final HTML report, tables, SVGs and PDFs (also zipped with a timestamp)
├── runs/                                       # agent outputs, one timestamped directory per run (gitignored)
└── README.md
```

## Requirements

| Component | Used for | Notes |
|---|---|---|
| **RSAT** (`rsat-core`, bioconda) | `matrix-scan`, `oligo-analysis` | Perl-based; tested with `rsat-core` 2025.04.04 and 2026.10.08 |
| Python ≥ 3.10 | notebook kernel | |
| `pyranges` (0.x), `pyfaidx`, `biopython`, `pandas`, `numpy` | GFF parsing, promoter extraction | the notebook uses the pyranges 0.x API (`Feature`, `five_end`, `slack`), so pin `pyranges<1`; pyfaidx needs `biopython` ≥ 1.73 to read the bgzipped genome from the GitHub Release |
| `matplotlib`, `pillow` | site map, CIS-BP logos | |
| `itables`, `session-info` | interactive tables, session record | |
| `pyyaml` | agent settings files | only needed for the Claude agent |
| `jupyter` / `ipykernel` | running the notebook | kernel name used: `python3` |
| **Quarto** (≥ 1.3) | rendering the final report (last cell) | needs a Jupyter kernel with the packages above |
| Mouse genome + annotation, CIS-BP PWMs | input data | see [Data](#2-input-data) |

Disk: the genome FASTA is ~2.8 GB, the GFF ~0.9 GB.

## Installation

### 1. Environments

Two separate environments are used: RSAT lives in its own conda environment (it is a Perl tool, and its `bin` must lead
`PATH`, which the notebook handles); the notebook itself runs in a normal Python environment.

**Prerequisite: conda.** Install [Miniforge/Mambaforge](https://github.com/conda-forge/miniforge) (recommended) or Miniconda if
you do not have `conda`/`mamba`. Bioconda packages need the channels `conda-forge` and `bioconda`; the commands below pass them explicitly.

**a) RSAT environment (from bioconda)**

RSAT is not on PyPI; the only packaged install is the bioconda recipe
[`rsat-core`](https://anaconda.org/bioconda/rsat-core) (it brings Perl and its dependencies).

```bash
conda create -n rsat -c conda-forge -c bioconda rsat-core      # or: mamba create ...
conda env list                                                 # note the path of "rsat" -> RSAT_ENV in the notebook
```

Check it works:

```bash
conda activate rsat
rsat matrix-scan -h | head
```

Note that `matrix-scan` is not a standalone command: `rsat-core` dispatches every tool through the single `rsat`
entry point. The `matrix-scan-quick` binary that *is* on `PATH` is a different program. The env's `bin` must lead
`PATH` or the Perl shebang resolves to the system interpreter and the tool dies on missing modules.

**b) Notebook environment (conda + pip)**

```bash
conda create -n pybioinfo -c conda-forge -c bioconda python=3.12 pip jupyter ipykernel
conda activate pybioinfo

# Python packages (pip)
pip install "pyranges<1" pyfaidx biopython pandas numpy matplotlib pillow itables session-info pyyaml

# register the Jupyter kernel
python -m ipykernel install --user --name python3 --display-name pybioinfo
```

All Python dependencies can also come from conda (`-c conda-forge -c bioconda pyranges pyfaidx biopython pandas numpy matplotlib pillow itables session-info pyyaml`);
use one or the other, not both, within the same environment. Check with `python -c "import pyranges, pyfaidx, Bio, itables, session_info"`.

**c) Quarto (only for the final report cell)**

Install from <https://quarto.org/docs/get-started/> (a system install is fine; it just needs to be on `PATH`).
Quarto renders with the kernel of the active environment, so run it from `pybioinfo`; the notebook sets
`QUARTO_PYTHON` to the current interpreter.

### Known issue: Apple Silicon (M1/M2/M3…) Macs

`rsat-core` on bioconda is built for **linux-64, linux-aarch64 and osx-64 only, not osx-arm64**. On an Apple Silicon
Mac a plain `conda create … rsat-core` fails with *“package not found”*. Linux and Intel Macs are not affected.
Workarounds:

- **Rosetta (osx-64 build):**
  ```bash
  CONDA_SUBDIR=osx-64 conda create -n rsat -c conda-forge -c bioconda rsat-core
  conda activate rsat
  conda config --env --set subdir osx-64     # keep this env on osx-64 for later installs
  ```
- **Docker / Apptainer:** run RSAT from a container and point `RSAT_ENV`/the `rsat()` helper at it.
  Note that RSAT's `RSAT_config.bashrc` is appended to `/etc/bash.bashrc`, which bash reads only for *interactive*
  shells, so a one-shot `docker run … matrix-scan` will not find the tool unless the config is sourced explicitly.

### Known issue: `matrix-scan -bginput` is broken

RSAT's built-in background estimation fails at every Markov order with *“the sum must be strictly positive”*,
followed by a division by zero in `RSAT/matrix.pm`. Confirmed in bioconda `rsat-core` 2025.04.04 **and still present
in 2026.10.08**, so this is a permanent workaround, not a patch awaiting a fix. The background is therefore estimated
with `oligo-analysis` and passed via `-bgfile`: the same estimator over the same sequences, just made explicit.

Related: `matrix-scan` can print `Error` on **stdout while exiting 0**, so the return code alone is not a sufficient
check. The notebook's `rsat()` helper and the agent's `motifscan.py` both grep for it; do not simplify that away.

### 2. Input data

**Genome and annotation (NCBI RefSeq, GRCm39 / GCF_000001635.27)**

The quickest route is the bgzipped copy attached to the repo's GitHub Release
[`genome-GRCm39-GCF_000001635.27`](https://github.com/ADAorg/DNA_032_FTmotif_search_for_agent/releases/tag/genome-GRCm39-GCF_000001635.27)
(release assets are not part of git history and can be up to 2 GB each). This script downloads the bgzipped
FASTA (with its `.gzi`/`.fai` indexes) and the gzipped GFF, ~0.9 GB in all, checks the SHA-256 sums and keeps them
compressed; the notebook and the agent's scripts read the `.gz` files directly, so the 3.7 GB unpacked copy is
never needed. If the plain files are already in place they are used instead:

```bash
bash .claude/skills/ft-motif-search-skill/scripts/fetch_genome.sh
```

Or download it from NCBI directly:

```bash
datasets download genome accession GCF_000001635.27 --include genome,gff3 --filename mouse_GRCm39.zip
unzip mouse_GRCm39.zip -d tmp_ncbi
# place/rename into Data/ncbi_dataset_RefSeq_GCF_000001635.27/ as:
#   GCF_000001635.27_GRCm39_genomic.fna
#   genomic.gff
#   dataset_catalog.json        <- keep this: it records the expected file sizes
#   assembly_data_report.jsonl  <- keep this: it records the annotation release
```

(`datasets` is the [NCBI Datasets CLI](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/download-and-install/); the same files can be
downloaded from the NCBI genome page for GCF_000001635.27.) The `.fai` index is created automatically by pyfaidx on first use.
The two large files are in `.gitignore` — GitHub rejects anything over 100 MB, so the genome is never committed.

> **Verify the genome download.** An incomplete copy fails silently: the FASTA is still readable, but chromosomes past the
> cut-off come back as **empty promoter sequences**, so many genes have no sites and the map looks mostly empty.
>
> The quickest check is the agent's gate, which compares every file against the sizes NCBI recorded in
> `dataset_catalog.json` and verifies the annotation release:
> ```bash
> python .claude/skills/ft-motif-search-skill/scripts/check_genome.py \
>     Data/ncbi_dataset_RefSeq_GCF_000001635.27 \
>     --expect-annotation GCF_000001635.27-RS_2024_02
> ```
> Expected sizes, if you prefer to check by hand:
>
> | File | Bytes |
> |---|---|
> | `GCF_000001635.27_GRCm39_genomic.fna` | 2,762,330,512 |
> | `genomic.gff` | 921,533,202 |
>
> The `.fai` should list 61 sequences. After the extraction step,
> `Results/promoters_sequences.fasta` should contain one **2201 bp** sequence per gene:
> ```bash
> awk '/^>/{if(h)print h,n; h=$0; n=0; next}{n+=length($0)}END{print h,n}' Results/promoters_sequences.fasta | awk '$2!=2201'   # should print nothing
> ```

**CIS-BP motifs (Mus musculus)**

Download the *Mus musculus* PWM collection from [CIS-BP](https://cisbp.ccbr.utoronto.ca/) and unpack it as
`Data/Mus_musculus_<date>_CISBP/` containing `pwms_all_motifs/<ID>.txt` and `logos_used_motifs/<ID>_fwd.png|_rev.png`.
Motifs used: `M03221_3.10` (Spic), `M09222_3.10` and `M10174_3.10` (Nfe2l2), `M10181_3.10` (Bach1).

### 3. Set the local paths

Paths are hard-coded for the original machine. Edit these before running the notebook directly
(the Claude agent resolves them itself and does not need this step):

| Cell | Variable | Set to |
|---|---|---|
| `setup_packages_paths` | `PROJECT` | absolute path of this folder |
| `rsat_setup` | `RSAT_ENV` | path of the `rsat` conda env (`conda env list`) |
| `gene_subset` | `CISBP` | name of your CIS-BP folder in `Data/` |

## Running

1. Open the notebook with the kernel that has the Python packages.
2. **Run all cells** (the last cell, `render_report`, has `eval: false` and is run on demand).
3. To change the analysis, edit the `gene_subset` cell: `NETWORK_GENES` (genes whose promoters are extracted, scanned and mapped),
   `PROMOTER_UPSTREAM_BP` / `PROMOTER_DOWNSTREAM_BP`, `PVAL`, `MOTIFS`.

Genes not found among RefSeq Select transcripts are listed in the setup summary; look up an alternate symbol (UniProt) and rerun.
`Scd5` currently falls in this group.

## The Claude agent

This repository carries a Claude skill at `.claude/skills/ft-motif-search-skill/`.
[Claude Code](https://claude.com/claude-code) loads it automatically when started from the repository root —
there is nothing to install:

```bash
cd /path/to/DNA_032_FTmotif_search_for_agent
claude
```

Then ask in ordinary words, for example *“scan the promoters of Hmox1, Gclm and Nqo1 for Nfe2l2 and Bach1”*.
The agent will:

1. Verify the genome is complete and the annotation release is the expected one, and refuse to run otherwise.
2. Ask which transcription factor motifs to scan, in an option box (Spic, Nfe2l2_1, Nfe2l2_2, Bach1; one or more).
3. Ask for your gene symbols and check each against the RefSeq Select transcripts, in seconds rather than
   the minutes a full GFF parse costs.
4. **Stop and tell you which symbols were not found**, with a UniProt link for each, and wait for replacements.
5. Ask for the promoter length upstream of the TSS, in an option box (1 kb, 2 kb default, 5 kb, or any length you
   type from 1 kb up, with no upper limit; always plus 200 bp downstream).
6. Ask for the p-value threshold, in an option box (1e-4 default, 1e-3, 1e-5, or your own value).
7. Run the extraction and scan, reporting progress at each stage, show you the site map image and give you
   the site map as SVG and PDF files.
8. Ask whether you want the zip; if yes, render the HTML report and hand back a zip with the report, the site
   map (SVG, PNG and PDF), the hits CSV, the raw `.ft` file and the run record (`run_log.md`, `run_config.yaml`,
   `my_settings.yaml`).

Every run writes to its own `runs/<timestamp>/` directory. Nothing from a previous run is ever reused or
re-presented, and the agent does not modify any tracked file in this repository. Before reporting back, the
agent walks a checklist at the end of `SKILL.md` (genome verified, every choice taken from you, gene misses
resolved, outputs in the run directory, …) and tells you about any item it could not tick.

### What you can and cannot change

The agent reads an optional settings file. Create a starter with:

```bash
python .claude/skills/ft-motif-search-skill/scripts/runconfig.py --init my_settings.yaml
python .claude/skills/ft-motif-search-skill/scripts/runconfig.py --check my_settings.yaml
```

**You can change:** which transcription factors are scanned, the gene panel, the p-value, the upstream promoter
length (default 2 kb; the 200 bp downstream is fixed), and everything about
the figures — motif colours, width, row height, dpi, output formats (svg/png/pdf), title, sort order, font size,
legend — and what goes into the zip.

**Fixed:** the reference genome (species, accession, assembly, annotation release), the background model and
Markov order, pseudo-counts, strand handling, coordinate origin, the downstream promoter length, transcript selection,
matrix scaling and gene matching. These define the method; changing one produces results that look valid but
are not comparable with previous runs or with the published analysis.

A settings file that touches a fixed parameter is **rejected**, not silently ignored. If your work genuinely
needs a different value, contact **sara.salazar@gimm.pt** rather than editing the analysis.

Each run writes three files, and all three go into every zip:

| File | Content |
|---|---|
| `my_settings.yaml` | only your choices — share it and someone can reproduce your run exactly |
| `run_config.yaml` | your choices *plus* the fixed method parameters, so the report always records what produced it |
| `run_log.md` | what was run: repository commit (and whether it had uncommitted changes), genome check result, motifs, genes and any gene-check replacements, promoter window, p-value, whether promoters were re-extracted or reused, a table of every setting that differs from the defaults (or "none"), and any checklist item that could not be ticked |

`run_log.md` is written on every run, not only when something changed, so a run without one is never mistaken
for a run at defaults. The "changes from defaults" table is computed by `runconfig.py`, not written by hand:

```bash
python .claude/skills/ft-motif-search-skill/scripts/runconfig.py --log runs/<timestamp> \
    --settings runs/<timestamp>/my_settings.yaml --promoters re-extracted --genome-check passed
```

### Maintaining the skill

The skill lives only in `.claude/skills/ft-motif-search-skill/`; there is no packaged or installed copy to
rebuild. Claude Code picks it up from the repository root, and in claude.ai chat Claude clones this repository
from GitHub and follows the same `SKILL.md`. To change the agent, edit that folder and push.

The claude.ai sandbox cannot reach NCBI, but it can download GitHub Release assets, so the skill fetches the
genome with `fetch_genome.sh` (see [Input data](#2-input-data)) and can run the scan there.

## Outputs

| File | Content |
|---|---|
| `Results/promoters_sequences.fasta` | extracted promoter sequences (`>Gene\|TranscriptID`) |
| `Results/matrix_scan/scanmotif_*.ft` | raw RSAT `matrix-scan` output (header records matrices, pseudo-counts, background) |
| `Results/matrix_scan/sitemap_*.svg`, `.pdf` | site map: one lane per scanned promoter, markers = motif sites (▲ direct, ▼ reverse), size ∝ significance |
| `Results/motifs_coordinates_*.csv` | one row per site: sequence, promoter position, distance to TSS, genomic coordinates and strand |
| `Results/results_report/` | HTML report, tables and figures; also packaged as `results_report_<timestamp>.zip` |
| `runs/<timestamp>/` | the same set of outputs when the analysis is run through the Claude agent, plus `my_settings.yaml`, `run_config.yaml` and `run_log.md` |

Promoters with no site still get a (grey) lane in the map. Positions are relative to the TSS (TSS = 0, upstream negative).

Keep the `;` comment lines at the top of any `.ft` file: they are the authoritative record of the matrices,
pseudo-counts and background model that produced the scan, and `pd.read_csv(…, comment=";")` discards exactly
those lines.

## Troubleshooting

- **Few genes with sites / empty promoters:** truncated genome file, see the verify step above.
- **`rsat` not found / Perl errors:** `RSAT_ENV` is wrong; the notebook runs `rsat` by full path and puts the env's `bin` first on `PATH`.
- **`package not found: rsat-core`** on a Mac: Apple Silicon issue above.
- **`the sum must be strictly positive` / division by zero in `matrix.pm`:** `-bginput` is broken; use the
  `oligo-analysis` + `-bgfile` route, as the notebook and the agent both do.
- **`Not found:` genes in the setup summary:** symbol is not a RefSeq Select mRNA in this annotation; try the alternate symbol.
- **Quarto warnings at the end of `render_report`:**
  ```
  WARN: Refusing to remove directory .../Results/results_report/..._files since it is not a subdirectory of the main project directory.
  WARN: Quarto did not expect the path configuration being used in this project, and strange behavior may result.
  ```
  These are warnings, not failures: the report (`..._report.html`) and the zip are still created ("Output created", "Report:", "Archive:").
  They appear because the output directory (`Results/results_report`) is outside the Quarto project directory (`Notebooks/`).
  Quarto therefore will not clean its `..._files` folder, so stale figures from a previous render can remain there and the folder
  may need to be deleted manually before a re-render. To remove the warning, render from the project root (add a `_quarto.yml` there) instead of `Notebooks/`.
- **pyranges attribute errors (`Feature`, `five_end`):** pyranges ≥ 1.0 installed; use `pyranges<1`.

## Note on gene matching

The notebook's `scan()` selects promoters with a case-insensitive **substring** test against the FASTA header.
This is safe as used, because an earlier exact filter has already narrowed the FASTA to the requested panel, and
no symbol in the current panel is contained in another — the published results are unaffected. It would not be
safe for an arbitrary gene list (`Cat` would also match `Cat1`), so the agent's `motifscan.py` matches the gene
field exactly and raises if any requested gene has no promoter.
