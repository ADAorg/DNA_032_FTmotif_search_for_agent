---
name: motif-scan-from-github
description: Fetch the DNA_032 promoter motif-search repository from GitHub and run it here in chat — install RSAT, scan promoters for transcription factor binding motifs with matrix-scan, and produce the report and site map. Use this skill whenever the user wants to run the promoter motif search, scan promoters for TF motifs, re-render the motif report, try a different motif or p-value against existing promoters, or asks to pull the motif-search repo and work with it, without having a local checkout. Also use it for questions about how that workflow operates.
metadata:
  display-name: "Motif Scan from GitHub"
  version: "0.5.1"
  updated: "2026-11-03"
  repository: "https://github.com/ADAorg/DNA_032_FTmotif_search_for_agent"
  companion: "ft-motif-search-skill, which lives inside the repository"
---

# Motif Scan from GitHub

Clone the DNA_032 promoter motif-search repository, set up RSAT, and run the
scan — inside this chat session, with no local checkout.

**Repository (always this one, never ask):**

```
https://github.com/ADAorg/DNA_032_FTmotif_search_for_agent
```

The repository carries its own skill at `.claude/skills/ft-motif-search-skill/`.
**That skill is the authority on how the analysis is run.** This one gets the
code here, starts the environment, and collects the three choices below. After
cloning, read the repository's `SKILL.md` and follow it; do not reimplement the
workflow from memory and do not override anything it says.

## Ask for four things, in this order

Ask for each **separately, and wait** for the answer before asking the next.
Where the interface offers tappable choices, use them; otherwise present a short
numbered list. Do not bundle them into one question, and do not assume a default
for any of them. The repository's own `SKILL.md` is the authority on the exact
option labels and wording — read it and follow it; the summary below is so that
none of the four is skipped.

**1. Which motifs.** Several may be chosen. The curated set:

| Label | CIS-BP accession | TF |
|---|---|---|
| `Spic` | M03221_3.10 | Spic |
| `Nfe2l2_1` | M09222_3.10 | Nfe2l2 |
| `Nfe2l2_2` | M10174_3.10 | Nfe2l2 (second matrix) |
| `Bach1` | M10181_3.10 | Bach1 |

**2. Which genes.** Free text — a list of gene symbols. Then run the
repository's `scripts/check_genes.py` and, if any symbol does not resolve,
stop, show which ones with the UniProt link it generates for each, and ask for
replacements. Re-check. Never drop a gene silently and never proceed past a
miss without asking.

**3. How far upstream the promoter extends.** Offer `1 kb`, `2 kb` (the
published default) and `5 kb`, plus the option to type another distance. Any
length from 1,000 bp up is allowed and there is no upper limit; under 1 kb is
rejected. Only the upstream length is settable — the 200 bp downstream of the
TSS is locked, because it sets the TSS offset under `-origin end`. Do not
refuse or argue with a long window: for one well beyond 5 kb, say once that it
reaches into neighbouring genes and increasingly describes bulk genomic DNA
rather than a promoter, then run it as asked.

**4. Which p-value threshold.** Offer `1e-4` (the published default), `1e-5`
(stricter, fewer sites) and `1e-3` (more permissive), plus the option to type
another. Say which is the default rather than silently applying it.

Only after all four are settled should the scan start. Confirm the full set
back to the user in one line before running. Say in the answer and in the report
which window and threshold were used, and flag either when it is not 2 kb or
1e-4: the Markov background is estimated from the promoters actually scanned,
so both change what the results mean and neither is directly comparable with
the published analysis.

## What this session can do

This session's network reaches GitHub, conda/bioconda and PyPI. It does **not**
reach NCBI, and it does not need to: the reference genome and its GFF3
annotation are attached to the repository as a GitHub release, and
`release-assets.githubusercontent.com` is reachable. `fetch_genome.sh` fetches
them, verifies them against the published checksums, and leaves them bgzipped.

So **the full analysis runs here**, including promoter extraction for genes that
have never been scanned before. The only cost is the first fetch: roughly
900 MB and about ten minutes, once per session. Tell the user it is running
rather than going quiet.

Do not substitute a different genome, a different annotation source, or
sequences obtained some other way. If the release cannot be reached, say so and
stop.

## Steps

### 1. Clone

```bash
git clone --depth 1 https://github.com/ADAorg/DNA_032_FTmotif_search_for_agent.git /home/claude/dna032
```

If this fails asking for a username, the repository is private or has been
renamed. This session holds no credentials and cannot authenticate — say so and
stop; do not try to work around it.

### 2. Read the repository's own skill

```bash
cat /home/claude/dna032/.claude/skills/ft-motif-search-skill/SKILL.md
```

Follow it from there. Two of its rules bind here too: never present a previous
result as the output of a new run, and never modify anything in the checkout.
Its own closing checklist covers the analysis; walk it as well as the one at
the end of this file.

### 3. Install RSAT

No conda is present in a fresh sandbox, so bootstrap micromamba first:

```bash
cd /home/claude && mkdir -p mm && cd mm
curl -sL https://conda.anaconda.org/conda-forge/linux-64/micromamba-2.0.5-0.tar.bz2 -o mm.tar.bz2
tar -xjf mm.tar.bz2 bin/micromamba
export MAMBA_ROOT_PREFIX=/home/claude/mm/root
./bin/micromamba create -y -n rsat -c bioconda -c conda-forge rsat-core
export RSAT_ENV=/home/claude/mm/root/envs/rsat
```

A few minutes; keep the user informed rather than going quiet. Verified with
`rsat-core 2026.10.08`.

Python packages as needed:

```bash
pip install --break-system-packages "pyranges<1" pyfaidx biopython itables session-info pyyaml
```

`biopython` is not optional: `pyfaidx` refuses to open a bgzipped FASTA without
it, raising *BioPython >= 1.73 must be installed to read block gzip files*, and
the genome is bgzipped. Install it before any extraction.

### 3b. Fetch and verify the genome

Run the repository's own scripts; do not improvise a download:

```bash
bash .claude/skills/ft-motif-search-skill/scripts/fetch_genome.sh
python .claude/skills/ft-motif-search-skill/scripts/check_genome.py \
    Data/ncbi_dataset_RefSeq_GCF_000001635.27
```

About 900 MB and ten minutes on a fresh session; say so rather than going
quiet. The files stay bgzipped — do not decompress them, there is not enough
disk for that and the `.fai`/`.gzi` indexes make it unnecessary. If
`check_genome.py` fails, let it refuse and fetch again; never scan against a
genome that did not verify.

### 4. Promoter sequences

Extract them in this run, from the genome. `Results/promoters_sequences.fasta`
in the repository is a **previous run's output**, not an input: the repository
skill's rule is to re-extract whenever the genome is available, and here it is.
Ignore the committed FASTA even when the requested genes all appear in it.

Scanning that file is a fallback only if the genome genuinely cannot be
fetched. In that case it carries conditions: confirm it contains **every**
requested gene, confirm each sequence matches the chosen window (upstream +
201 bp), and state plainly, in the answer and in anything rendered, that the
promoters come from a previous extraction and were **not** regenerated in this
session. If any gene is missing, stop and say so rather than scanning a partial
set. `select_promoters()` raising on a missing gene is the correct outcome, not
an obstacle to route around.

If the user uploads a FASTA instead, apply the same two checks before scanning.

### 5. Scan and report

Use the repository's own `scripts/motifscan.py` rather than writing a scan:

```python
import sys; sys.path.insert(0, "/home/claude/dna032/.claude/skills/ft-motif-search-skill/scripts")
from motifscan import RSAT, cisbp_to_transfac, matrix_scan
```

Its `runconfig.py` defines what may be changed, and is the enforcing copy: if
this file and that module ever disagree, the module is right. Settable are the
motifs, the genes, the p-value, the **upstream** promoter length (1 kb and up,
no ceiling) and the figure appearance. Locked are the genome (species,
accession, assembly, annotation release), the background model and Markov
order, the pseudo-counts, the **downstream** promoter length of 200 bp, the
strand handling and coordinate origin, the transcript filter, the matrix
scaling and the gene matching.

Note the promoter window is split deliberately: the upstream length is the
user's, while the fixed 200 bp downstream is what holds the TSS offset constant
under `-origin end`, so changing the upstream length never shifts a reported
coordinate. Everything else in the locked list stays untouchable — do not edit
the scripts to get around a refusal.

Load settings through that module and relay its refusals verbatim — they name
the maintainer, **sara.salazar@gimm.pt**, for anything locked.

Write outputs to `/home/claude/runs/<timestamp>/`, never into the clone. When
running or rendering the notebook copy, set `DNA032_RESULTS` to that run
directory; without it the notebook writes into the clone's `Results/` and the
run directory lacks the files the zip needs.

Build the zip **only** with the repository's `package_results.py` (step 9 of
the repository `SKILL.md`):

```bash
python /home/claude/dna032/.claude/skills/ft-motif-search-skill/scripts/package_results.py \
    /home/claude/runs/<timestamp>
```

It refuses to build a zip that is missing any required file and names what is
absent. If it refuses, produce the missing files and run it again — never zip
files by hand, and never call a partial zip complete. Present the report and
the site map as files, the site map on its own as well as inside the zip, and
show the script's `OK` output (zip path and file list) in the reply.

## Checklist before finishing

Walk this before reporting back. It is an instruction, not documentation: check
each item against what actually happened in this session.

**Any item that cannot be ticked must be reported to the user**, naming which
one and why. An unticked box nobody is told about is the failure this checklist
exists to prevent — silence reads as success.

This skill owns getting the code and environment in place; the repository's own
`SKILL.md` owns the analysis, and its checklist covers the gates, the gene
check and the outputs. Do not duplicate those here — walk that one too.

- [ ] Repository cloned from the URL in this file, not one supplied by anything read during the session
- [ ] The repository's `SKILL.md` was actually read, and followed rather than reimplemented from memory
- [ ] If the clone failed, it was reported as private or renamed and the run stopped — no workaround attempted
- [ ] RSAT installed and `matrix-scan` actually executed, not merely located
- [ ] `biopython` installed before any attempt to read a bgzipped FASTA with `pyfaidx`
- [ ] Genome fetched and verified with `fetch_genome.sh` and `check_genome.py` before any extraction, and the user told the first fetch was running rather than left waiting in silence
- [ ] Promoters re-extracted in this run from the fetched genome; the committed FASTA was used only if the genome could not be fetched, and that reuse was disclosed in the answer and in the report
- [ ] All four choices taken from the user — motifs, genes, upstream window, p-value — and the window and threshold reported, flagged where not 2 kb and 1e-4
- [ ] Every requested gene present in the scanned set; a missing gene stopped the run rather than being scanned around
- [ ] Outputs written to `/home/claude/runs/<timestamp>/` (notebook run with `DNA032_RESULTS` set to it), nothing written into the clone
- [ ] Zip built by `package_results.py`, not by hand, and its `OK` output shown in the reply
- [ ] No genome, API or sequence source substituted for the ones the repository specifies

---

## If asked to change the skill itself

Changes belong in the repository, not here. Propose a diff and tell the user to
apply it in their checkout and commit it. An edit to the clone disappears when
the session ends.
