# DNA_032 – Transcription-factor motif search in mouse promoters

Scans the promoters of a gene panel (the *Spic* / Nfe2l2 / ferroptosis network) for binding sites of
SpiC, Nfe2l2 (two matrices) and Bach1, and produces a site map and a coordinate table.

**What the notebook does**

1. Reads the RefSeq GRCm39 annotation and keeps the **RefSeq Select** (canonical) transcript of each gene.
2. Builds strand-aware promoter windows (default **−2000 / +200 bp** around the TSS) and extracts them from the genome.
3. Loads the CIS-BP PWMs for the TFs, converts them to TRANSFAC format.
4. Scans the promoters with RSAT `matrix-scan` (P < 1e-4, order-1 Markov background estimated from the scanned promoters).
5. Draws the site map, converts hits to genomic coordinates, and renders/zips an HTML report.

Everything is in one notebook: [Notebooks/PromoterExtraction_adapted_with_rsatconda_refseqannotation.ipynb](Notebooks/PromoterExtraction_adapted_with_rsatconda_refseqannotation.ipynb)
(Quarto-annotated Jupyter notebook).

## Project structure

```
DNA_032_FTmotif_search_for_agent/
├── Data/
│   ├── ncbi_dataset_RefSeq_GCF_000001635.27/   # genome FASTA + GFF3 annotation (not in git, see below)
│   └── Mus_musculus_<date>_CISBP/              # CIS-BP download: pwms_all_motifs/, logos_used_motifs/
├── Notebooks/                                  # the analysis notebook
├── Results/
│   ├── promoters_sequences.fasta               # extracted promoters (regenerated on every run)
│   ├── motifs_coordinates_SpiC_network_all_TFs.csv
│   ├── matrix_scan/                            # RSAT inputs/outputs: .tf matrices, .ft scan, sitemap/logo SVGs
│   └── results_report/                         # final HTML report, tables, SVGs (also zipped with a timestamp)
└── README.md
```

## Requirements

| Component | Used for | Notes |
|---|---|---|
| **RSAT** (`rsat-core`, bioconda) | `matrix-scan`, `oligo-analysis` | Perl-based; tested with `rsat-core 2025.04.04` |
| Python ≥ 3.10 | notebook kernel | |
| `pyranges` (0.x), `pyfaidx`, `pandas`, `numpy` | GFF parsing, promoter extraction | the notebook uses the pyranges 0.x API (`Feature`, `five_end`, `slack`), so pin `pyranges<1` |
| `matplotlib`, `pillow` | site map, CIS-BP logos | |
| `itables`, `session-info` | interactive tables, session record | |
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

**b) Notebook environment (conda + pip)**

```bash
conda create -n pybioinfo -c conda-forge -c bioconda python=3.12 pip jupyter ipykernel
conda activate pybioinfo

# Python packages (pip)
pip install "pyranges<1" pyfaidx pandas numpy matplotlib pillow itables session-info

# register the Jupyter kernel
python -m ipykernel install --user --name python3 --display-name pybioinfo
```

All Python dependencies can also come from conda (`-c conda-forge -c bioconda pyranges pyfaidx pandas numpy matplotlib pillow itables session-info`);
use one or the other, not both, within the same environment. Check with `python -c "import pyranges, pyfaidx, itables, session_info"`.

**c) Quarto (only for the final report cell)**

Install from <https://quarto.org/docs/get-started/> (a system install is fine; it just needs to be on `PATH`).
Quarto renders with the kernel of the active environment, so run it from `pybioinfo`; the notebook sets
`QUARTO_PYTHON` to the current interpreter.

Check RSAT works:

```bash
$CONDA_PREFIX/bin/rsat matrix-scan -h | head      # run with the rsat env active, or use its full path
```

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

### 2. Input data

**Genome and annotation (NCBI RefSeq, GRCm39 / GCF_000001635.27)**

```bash
datasets download genome accession GCF_000001635.27 --include genome,gff3 --filename mouse_GRCm39.zip
unzip mouse_GRCm39.zip -d tmp_ncbi
# place/rename into Data/ncbi_dataset_RefSeq_GCF_000001635.27/ as:
#   GCF_000001635.27_GRCm39_genomic.fna
#   genomic.gff
```

(`datasets` is the [NCBI Datasets CLI](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/download-and-install/); the same files can be
downloaded from the NCBI genome page for GCF_000001635.27.) The `.fai` index is created automatically by pyfaidx on first use.
These large files are in `.gitignore`.

> **Verify the genome download.** An incomplete copy fails silently: the FASTA is still readable, but chromosomes past the
> cut-off come back as **empty promoter sequences**, so many genes have no sites and the map looks mostly empty.
> The complete `GCF_000001635.27_GRCm39_genomic.fna` is **2,762,330,512 bytes**; the `.fai` should list 61 sequences.
> After the extraction step, `Results/promoters_sequences.fasta` should contain one **2201 bp** sequence per gene.
> ```bash
> ls -l Data/ncbi_dataset_RefSeq_GCF_000001635.27/*.fna
> awk '/^>/{if(h)print h,n; h=$0; n=0; next}{n+=length($0)}END{print h,n}' Results/promoters_sequences.fasta | awk '$2!=2201'   # should print nothing
> ```

**CIS-BP motifs (Mus musculus)**

Download the *Mus musculus* PWM collection from [CIS-BP](https://cisbp.ccbr.utoronto.ca/) and unpack it as
`Data/Mus_musculus_<date>_CISBP/` containing `pwms_all_motifs/<ID>.txt` and `logos_used_motifs/<ID>_fwd.png|_rev.png`.
Motifs used: `M03221_3.10` (Spic), `M09222_3.10` and `M10174_3.10` (Nfe2l2), `M10181_3.10` (Bach1).

### 3. Set the local paths

Paths are hard-coded for the original machine. Edit these before running:

| Cell | Variable | Set to |
|---|---|---|
| `setup_packages_paths` | `PROJECT` | absolute path of this folder |
| `rsat_setup` | `RSAT_ENV` | path of the `rsat` conda env (`conda env list`) |
| `gene_subset` | `CISBP` | name of your CIS-BP folder in `Data/` |

## Running

1. Open the notebook with the kernel that has the Python packages.
2. **Run all cells** (the last cell, `render_report`, has `eval: false` and is run on demand).
3. To change the analysis, edit the `gene_subset` cell: `NETWORK_GENES` (genes scanned and mapped), `GENES_FOR_RETRIEVAL_ONLY`
   (promoters extracted but not mapped), `PROMOTER_UPSTREAM_BP` / `PROMOTER_DOWNSTREAM_BP`, `PVAL`, `MOTIFS`.

Genes not found among RefSeq Select transcripts are listed in the setup summary; look up an alternate symbol (UniProt) and rerun.
`Scd5` currently falls in this group.

## Outputs

| File | Content |
|---|---|
| `Results/promoters_sequences.fasta` | extracted promoter sequences (`>Gene\|TranscriptID`) |
| `Results/matrix_scan/scanmotif_*.ft` | raw RSAT `matrix-scan` output (header records matrices, pseudo-counts, background) |
| `Results/matrix_scan/sitemap_*.svg` | site map: one lane per scanned promoter, markers = motif sites (▲ direct, ▼ reverse), size ∝ significance |
| `Results/motifs_coordinates_*.csv` | one row per site: sequence, promoter position, distance to TSS, genomic coordinates and strand |
| `Results/results_report/` | HTML report, tables and figures; also packaged as `results_report_<timestamp>.zip` |

Promoters with no site still get a (grey) lane in the map. Positions are relative to the TSS (TSS = 0, upstream negative).

## Troubleshooting

- **Few genes with sites / empty promoters:** truncated genome file, see the verify step above.
- **`rsat` not found / Perl errors:** `RSAT_ENV` is wrong; the notebook runs `rsat` by full path and puts the env's `bin` first on `PATH`.
- **`package not found: rsat-core`** on a Mac: Apple Silicon issue above.
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
