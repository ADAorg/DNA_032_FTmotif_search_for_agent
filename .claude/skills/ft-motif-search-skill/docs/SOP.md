# SOP — FT Motif Search

**Scanning gene promoters for transcription-factor binding motifs**

| Field | Value |
|---|---|
| Document | SOP — FT Motif Search agent (project DNA_032) |
| Version | 0.8 |
| Date | 7 November 2026 |
| Applies to | `ft-motif-search-skill` (in repository) and `motif-scan-from-github` (chat) |
| Repository | https://github.com/ADAorg/DNA_032_FTmotif_search_for_agent |
| Owner / contact | Sara Salazar — sara.salazar@gimm.pt |

## Contents

- [1. Purpose](#1-purpose)
- [2. Scope and limitations](#2-scope-and-limitations)
  - [What the agent can do](#what-the-agent-can-do)
  - [What the agent cannot do](#what-the-agent-cannot-do)
- [3. Where to run it](#3-where-to-run-it)
- [4. Prerequisites](#4-prerequisites)
  - [In Claude.ai chat](#in-claudeai-chat)
  - [On your own machine](#on-your-own-machine)
- [5. Procedure](#5-procedure)
  - [Starting the agent](#starting-the-agent)
  - [The four questions](#the-four-questions)
  - [The gene check](#the-gene-check)
  - [Asking for changes to the figure](#asking-for-changes-to-the-figure)
  - [During the run](#during-the-run)
- [6. Results](#6-results)
  - [Interpreting results responsibly](#interpreting-results-responsibly)
- [7. The reference genome](#7-the-reference-genome)
- [8. Troubleshooting](#8-troubleshooting)
- [9. Contact and change control](#9-contact-and-change-control)
  - [Citing the method](#citing-the-method)

## 1. Purpose

This procedure describes how to search the promoters of a set of mouse genes for transcription-factor binding motifs, using the FT Motif Search agent. The agent extracts promoter sequences from the mouse reference genome, scans them with RSAT `matrix-scan` using CIS-BP position weight matrices, and returns an HTML report, a site map figure and a table of hit coordinates.

The analysis parameters are fixed so that results from different runs and different people remain comparable with each other and with the published method. You choose which motifs, which genes, how far upstream the promoter extends and which significance threshold; you do not choose how the scan is performed.

## 2. Scope and limitations

### What the agent can do

- Scan the promoters of any mouse gene present in the RefSeq GRCm39 annotation.
- Scan one or several of the four curated motifs: Spic, Nfe2l2_1, Nfe2l2_2, Bach1.
- Choose how far upstream of the TSS the promoter extends: 1 kb, 2 kb (default), 5 kb, or any distance you ask for from 1 kb up, with no upper limit. The 200 bp downstream of the TSS is fixed.
- Use a significance threshold of 1e-4 (default), 1e-3, 1e-5, or a value you supply.
- Tell you which of your gene symbols it could not find, with a UniProt link for each, and accept replacements before running.
- Change how the figures look: marker shape and size, colours, font weight and size, labels, title, legend, and the order of the promoters. Most of these are applied straight to the rendered site map (no re-run needed); figure size, layout, promoter sort order or anything else outside that is made in the figure code of a copy of the notebook inside your own run folder, never in the repository's.
- Say what it is about to do before each stage, and say beforehand when a stage takes time.
- Produce a zip containing the report, the site map as SVG, PNG and PDF, the hits table as CSV, the raw RSAT output and the run record (`run_log.md`, `run_config.yaml`, `my_settings.yaml`, `requested_changes.md`).
- Record the settings you chose in a file you can share, so a colleague can reproduce your run exactly.
- Keep a register of every change you asked for beyond the four questions, in `requested_changes.md` — applied, refused, not possible here, or needing the owner — so you can send it on or confirm nothing analytical changed.

### What the agent cannot do

- **Change the method.** The genome build, background model, pseudo-counts, strand handling, transcript selection, gene matching and the 200 bp downstream of the TSS are fixed. A request to change any of these is refused, not silently ignored.
- **Change where a motif lies in the promoter, or what the size of a marker means.** Site positions are the result itself, and marker size must keep growing as the p-value gets smaller. Everything else about the figure is yours to change.
- **Work on species other than mouse.** The analysis is validated for GRCm39 only.
- **Use motifs outside the curated set** without the matrices being added to the repository first.
- **Test for motif enrichment.** `matrix-scan` detects sites above a threshold; it does not compare against a background gene set. Describe results as *scanning*, not *enrichment*.
- **Modify anything in the repository.** Every run writes to its own output folder and leaves tracked files untouched. Figure edits go into a copy of the notebook in that folder.
- **Reuse an earlier result.** Each run recomputes everything; previous outputs are never presented as new ones.

> **If you need a different genome build, a different background model or another species, do not edit the analysis.** Contact sara.salazar@gimm.pt so the change can be made and validated once, for everyone.

## 3. Where to run it

There are two ways to use the agent, and both do the same analysis. The difference is only in setup.

Running it inside Claude.ai chat needs nothing installed: the agent clones the repository and fetches the reference genome itself. The first run in a fresh session spends about ten minutes on that download. The agent starts it in the background as soon as it has the code, and asks your four questions while it runs, so most of the wait overlaps with your answers. Running it on a machine where the project and the genome already exist skips the download entirely.

Neither route is more capable than the other. Both extract promoters for any gene in the annotation, both scan with the same engine, and both produce the same report. The reference genome is attached to the repository itself, so no route depends on reaching an external database at run time.

## 4. Prerequisites

### In Claude.ai chat

Install the skill once, from the file supplied with this SOP, using the **Save skill** button. Nothing else is required: the agent fetches the code, the reference genome and RSAT itself on first use.

### On your own machine

If you would rather run it locally, you need:

1. A clone of the repository, and Claude Code.
2. A conda environment containing RSAT:
   ```bash
   conda create -n rsat -c conda-forge -c bioconda rsat-core
   ```
3. A Python environment with `pyranges` (<1), `pyfaidx`, `biopython`, `pandas`, `numpy`, `matplotlib`, `pillow`, `itables`, `session-info` and `pyyaml`, plus Quarto for the report. `cairosvg` is optional, needed only so a visual change can regenerate the PNG and PDF to match an edited site map.

The agent fetches the genome if it is not already present.

**Note for Apple Silicon Macs:** RSAT has no `osx-arm64` build. Use `CONDA_SUBDIR=osx-64 conda create -n rsat -c conda-forge -c bioconda rsat-core` to run the Intel build under Rosetta, or a container. Linux and Intel Macs are unaffected.

## 5. Procedure

### Starting the agent

In chat, simply describe what you want. If you are running locally, start Claude Code from the project folder first (`cd` into the repository, then run `claude`). In both cases you do not need to name the skill; it starts automatically.

Ask in ordinary words, for example:

```
Scan the promoters of Hmox1, Gclm and Nqo1 for Nfe2l2 and Bach1
```

You can also just say "run the motif search" and answer the questions that follow.

### The four questions

The agent asks for four things, one at a time, and waits for each answer. Answer them in order; do not expect it to guess.

1. **Which motifs.** Choose one or more of Spic, Nfe2l2_1, Nfe2l2_2 and Bach1. Nfe2l2 has two matrices in CIS-BP; selecting both is normal and they are reported separately.
2. **Which genes.** Give official mouse gene symbols, separated by commas or spaces. Case does not matter.
3. **How far upstream the promoter extends.** 1 kb, 2 kb (recommended) or 5 kb, or type any distance from 1,000 bp up; there is no upper limit, and anything under 1 kb is rejected. Only the upstream length is yours to set: the 200 bp downstream of the TSS is fixed, because that is what keeps coordinates comparable when the upstream length changes.
4. **Which p-value threshold.** 1e-4 is the published default. 1e-5 is stricter and returns fewer sites; 1e-3 is more permissive and returns more. You may type another value.

> **Two of your four choices affect comparability.** The published analysis used a 2 kb upstream window and p ≤ 1e-4. If you change either, the agent says so in the answer and in the report — results from a different window or threshold are not directly comparable with it, because the background model is estimated from the promoters actually scanned.

### The gene check

Before scanning, the agent checks every symbol against the annotation. If any symbol has no canonical (RefSeq Select) transcript, it stops and lists them with a UniProt link for each.

Gene symbols change over time, and the alternative name is usually one click away in UniProt. Supply the replacement symbols; the agent re-checks and continues. You may also tell it to proceed without a gene, but it will never drop one silently.

A symbol can be missing for several reasons: it has been renamed; it is a human symbol rather than a mouse one (mouse symbols are capitalised as `Hmox1`, not `HMOX1`); it is a pseudogene or non-coding gene with no mRNA; or it is misspelled.

### Asking for changes to the figure

Ask for any visual change in ordinary words, for example "make the markers circles", "bold the title" or "drop Sqstm1 from the picture". The agent applies most of these directly to the already-rendered site map, then regenerates the PNG and PDF to match, so nothing is re-run. A change outside that — figure size, layout, the order of the promoter lanes — is made in the figure code of a copy of the notebook in your run folder, which is re-rendered so the figure and the report still come from the same notebook.

Two things it will not change: where a motif lies in the promoter, and what marker size means (a smaller p-value always gives a larger marker). Making all markers, or all text, larger or smaller together is fine.

If a change would hide information the figure shows, the agent says so once and offers a way to keep it. Circles instead of triangles, for example, would hide the strand, which the triangles show by pointing up or down; filled and open circles would keep it. Whichever way a change is applied, it is recorded in `requested_changes.md` — for a change applied directly to the site map, that entry is written by the tool that made it, from what it actually changed, so it can be checked against the hits table and raw scan rather than taken on trust; for a change made by editing the notebook copy instead, the entry is the actual code used, not a description of it, so you can read for yourself that it only draws the figure and computes nothing. A request that cannot be applied at all — most often because it asks to change the method, not the presentation — is recorded there too, with the reason.

### During the run

The agent says what it is about to do before each stage, says so when a stage will take time, and reports again when it ends. Long steps run in the background and are checked every few minutes, so you hear from it between checks. A first run that must download the genome takes around fifteen minutes in total, much of it while you answer the questions; afterwards a typical scan of thirty to forty promoters takes a few minutes, most of it the motif scan itself.

Before it packages anything, the agent checks that what it produced is what you asked for: the same genes, the same promoter window, the same p-value and motifs, and that the repository is unchanged. If that check fails, nothing is packaged and the agent tells you why.

Before packaging the results, the agent shows you the site map so you can check it looks sensible, and gives you the site map as SVG and PDF files to keep. It then asks whether you want the zip with the full report.

Before reporting back, the agent walks a closing checklist and tells you about any step it could not complete. Treat such a message as part of the result.

## 6. Results

Each run writes to its own timestamped folder, so runs never overwrite one another. You receive:

| File | Contents |
|---|---|
| HTML report | The full analysis: parameters, motif logos, site map, hits table |
| Site map (SVG, PNG and PDF) | One lane per promoter, markers for each site. Triangle up = forward strand, triangle down = reverse; marker size reflects significance; TSS at position 0, upstream negative |
| Hits table (CSV) | One row per site: gene, motif, strand, position relative to TSS, sequence, score, p-value, genomic coordinates |
| Raw RSAT output (`.ft`) | The scan as RSAT produced it. The `;` comment lines at the top record the exact parameters — keep them |
| `run_log.md` | What actually happened in the run: repository version, genome check result, motifs, genes and any gene replacements, promoter window, p-value, whether promoters were re-extracted, every setting that differs from the defaults (or "none"), and anything the agent could not complete. Written on every run |
| `my_settings.yaml` | The choices you made. Share this and a colleague reproduces your run exactly |
| `run_config.yaml` | Your choices plus the fixed method parameters, as a record of what produced the report |
| `requested_changes.md` | Every change you asked for beyond the four questions, with what was done: applied, refused, not possible here, or needing the owner. A visual change applied directly to the site map is logged by the tool that made it, from what it actually changed, not written from memory. Written on every run, even when it only says that nothing was asked |

The last four files go into every zip, so a package always records how it was made and what was asked of it.

The zip is built by `scripts/package_results.py`, never by hand. That script first checks that the run matches what you asked for (section 5), holds this list as code, and refuses to build a zip that is missing any of these files, naming what is absent. If this table and the script ever disagree, the script is right; update the table. The zip and its file list are shown to you when it is built. If a file was deliberately left out, the agent tells you which one and why.

Promoters with no site above the threshold still appear in the site map as an empty lane. This is a result, not a failure — it means no match was found at that significance.

### Interpreting results responsibly

- A predicted site is a sequence match, not evidence of binding. Confirmation requires experimental data such as ChIP, together with evidence that transcription of the gene actually changes.
- The scan reports sites above a threshold. It does not test whether your gene set is enriched for a motif relative to other genes.
- A lower p-value returns fewer, stronger matches; it does not make them more likely to be real binding sites.
- A longer promoter window finds more sites simply because it searches more sequence, and it also changes the background model. Do not compare site counts between runs that used different windows. Well beyond 5 kb the window reaches into neighbouring genes and increasingly describes bulk genomic DNA rather than a promoter; the agent will say so once and then run it as asked.
- Nfe2l2 and Bach1 recognise overlapping sequences, so sites for both at the same position are expected and not an error.
- If you changed how the figure looks, say so when you use it, and keep `requested_changes.md` with it — it names what was changed. The positions and the size-to-significance relationship are unchanged, but the figure is no longer the default one.

## 7. The reference genome

The analysis uses the NCBI RefSeq reference for mouse, **GRCm39 (GCF_000001635.27)**, annotation release **RS_2024_02**, and takes the **RefSeq Select** transcript of each gene.

RefSeq Select names one representative transcript per protein-coding gene, so it gives the most consensual definition of where a gene — and therefore its promoter — begins. That is why it is preferred here over annotations that enumerate many alternative isoforms: with several transcription start sites per gene there is no single promoter to scan, and the choice between them would change the result.

The genome is too large to include in the repository (2.7 GB of sequence and 0.9 GB of annotation), so it is attached to the repository as a release (tag `genome-GRCm39-GCF_000001635.27`) and downloaded on first use. Where it is already present, nothing needs doing.

Before the first run the agent also writes a small copy of the annotation holding only the RefSeq Select transcripts (`genomic.refseq_select_mrna.gff`, about 6 MB). The analysis reads that instead of the full 0.9 GB file, which would need about 11 GB of memory to load. It selects exactly the same transcripts — this was checked by rendering the report both ways and comparing every result file — and the report states which annotation file it read.

> **The agent verifies the genome before every run** and refuses to continue if the files are incomplete or from the wrong annotation release. An incomplete genome produces empty promoters and a report that looks sparse rather than broken, so this check is not optional. If it fails, let it refuse and re-download rather than working around it.

## 8. Troubleshooting

| Symptom | Cause and action |
|---|---|
| `package not found: rsat-core` | Apple Silicon Mac. Use the `CONDA_SUBDIR=osx-64` command in section 4, or a container |
| `BioPython >= 1.73 must be installed to read block gzip files` | Install `biopython` into the Python environment |
| Genome check fails or refuses to run | The genome is incomplete or the wrong release. Delete the files and let the agent download them again |
| The agent says it cannot extract promoters | The genome is missing or failed its check. Let `fetch_genome.sh` download it again; do not supply a substitute |
| Many genes with no sites at all | Usually a truncated genome; run the genome check. If the genome verifies, the result may be real |
| A gene symbol is not found | See section 5. Look it up in UniProt and supply the current mouse symbol |
| The agent refuses a change you asked for | You have asked to change the method, not the presentation. Note the upstream promoter length **is** settable; the 200 bp downstream is not. Contact the owner (section 9) |
| The agent asks for a repository URL | The repository is temporarily private. Contact the owner |
| The agent says the run does not match what you asked for | The check before packaging found, for example, genes you did not ask for, a different window or p-value, or a changed repository file. Nothing was packaged. Start a new run and do not ask it to zip the old one. If it keeps happening, send the owner the message and `run_log.md` |
| A visual request was refused | Only moving where a motif lies, or changing what marker size means, is refused. Anything else visual should be applied. If it was refused for another reason, send the owner `requested_changes.md` |
| `requested_changes.md` says "needs the owner" | The change needs a code or method change, not a setting. Send the file to the owner (section 9) |
| The agent reports that a step was stopped after about five minutes | A single step is limited to five minutes in chat. Long steps run in the background and are checked in rounds. Ask it to restart the same step; it resumes where it left off |

If the agent reports an error you do not recognise, keep the full message. It quotes the command that failed, which is usually enough to identify the cause.

## 9. Contact and change control

For anything this SOP does not cover, and in particular for any change to the method, contact:

**Sara Salazar · sara.salazar@gimm.pt**

Contact the owner when you need:

- A different background model, genome build or species.
- Motifs beyond the four curated ones, or matrices from another database.
- Motif enrichment testing rather than site scanning.
- A change to the report format or to the analysis code.
- Access to the repository, if it is private when you try to use it.
- A visual change you want made permanent, or one that needs a code change. Send the `requested_changes.md` from your run.

> **Confirm final results with a local run.** A chat session is convenient for exploring, but results that will appear in a figure or a manuscript should be reproduced on a machine you control, where the genome, the environment and the output files are all under your own version control.

Do not edit the analysis code, the notebook or the skill to work around a refusal. Results produced by a modified method are not comparable with anyone else's, and the difference will not be visible in the report. Changes are made once, centrally, and validated — which is also how they reach everyone else who needs them.

*When reporting a problem, include: what you asked for, the full error message, whether you ran in chat or locally, and the run folder name if one was created.*

### Citing the method

Describe the analysis as scanning with *matrix-scan* from the Regulatory Sequence Analysis Tools suite (Turatsinze et al., 2008), scanning both strands with a first-order Markov background model estimated from the input promoter sequences, a pseudo-count of 1 distributed proportionally to residue priors, and the p-value threshold you used. State the promoter window, the CIS-BP matrix identifiers, and the genome assembly and annotation release — all of which are recorded in `run_config.yaml` and in the report.
