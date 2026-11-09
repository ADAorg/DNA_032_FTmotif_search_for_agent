---
name: motif-scan-from-github
description: Fetch the DNA_032 promoter motif-search repository from GitHub and run it here in chat — install RSAT, scan promoters for transcription factor binding motifs with matrix-scan, and produce the report and site map. Use this skill whenever the user wants to run the promoter motif search, scan promoters for TF motifs, re-render the motif report, try a different motif or p-value against existing promoters, or asks to pull the motif-search repo and work with it, without having a local checkout. Also use it for questions about how that workflow operates.
model: sonnet
metadata:
  display-name: "Motif Scan from GitHub"
  version: "0.8.0"
  updated: "2026-11-07"
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

## Start the setup first

Do steps 1 and 2 (clone, read the repository skill). Then start steps 3 and 3b
**in the background, in parallel**, and ask the four questions below while they
run. Setup takes about ten minutes and the user's answers take a minute or two,
so otherwise those minutes are simply lost. Tell the user that setup is running
in the background and that you will ask four questions meanwhile.

- Start each job with `setsid nohup`, as shown in steps 3 and 3b. A job started
  as part of an ordinary command can be killed when that command ends or times
  out; in a test run the RSAT install died partway for exactly that reason.
- Each job writes `STAGE` lines to its own log. Check the logs in rounds, as
  described under *Keeping the user informed*.
- Do not start the scan until `rsat_install.log` ends with `STAGE rsat done`,
  `genome_fetch.log` ends with `STAGE genome done`, and the genome check passed.
- If a job's process is gone without its `done` line, start the same command
  again. The RSAT install resumes from the package cache, and `fetch_genome.sh`
  skips what it already has and verifies it.
- If the genome check fails after the user has answered the questions, say so
  then. It is the same refusal as before, only reached later.
- Check free disk space (`df -h /home/claude`) before starting. If a job fails
  with a disk error, say so and stop; delete nothing outside the run directory,
  the micromamba tree or the genome folder.

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

**3. How far upstream the promoter extends.** Offer `1 kb`, `2 kb (Recommended)`
and `5 kb`, plus the option to type another distance. Any
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

## Keeping the user informed

The user only hears from you between commands. Nothing reaches them while a
command is running, so say what is about to happen **before** starting it, not
during it.

Two limits shape how long steps are run:

- A single command is stopped after **300 seconds**, and what it was doing may
  be lost. Any step that can take longer than that runs in the background
  (`nohup ... > <log> 2>&1 &`) and is checked in short rounds.
- Each round is **one command that waits at most 4 minutes in total** (for
  example 8 checks 30 seconds apart). Never write a wait loop whose total is
  longer. After each round, tell the user which stage it has reached.

For every stage, send three short messages:

1. **Before** it starts: what is about to happen, and whether it takes time.
2. **During** a long stage, after each round: that it is still running, and
   which stage.
3. **After** it finishes: the result, in one line, before the next stage begins.

Expected times, so the messages are consistent:

| Stage | Expected time |
|---|---|
| Clone | seconds |
| Install RSAT | a few minutes |
| Fetch the genome (first run in a session only, about 900 MB) | about ten minutes |
| Install Quarto (pinned, from PyPI) | about half a minute (measured: 33 s) |
| Scan and render, for thirty to forty promoters | a few minutes |
| Anything else | no time has been measured: say it may take a while, and do not quote a number |

Do not invent a time for a stage that is not in the table. When the real time of
a stage has been measured, put it in the table.

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

No conda is present in a fresh sandbox, so bootstrap micromamba first. Run this
detached, and pinned to the RSAT version the scan was validated on:

```bash
cd /home/claude && mkdir -p mm runs
setsid nohup bash -c '
  set -e
  echo "STAGE rsat start"
  cd /home/claude/mm
  curl -sL https://conda.anaconda.org/conda-forge/linux-64/micromamba-2.0.5-0.tar.bz2 -o mm.tar.bz2
  tar -xjf mm.tar.bz2 bin/micromamba
  export MAMBA_ROOT_PREFIX=/home/claude/mm/root
  ./bin/micromamba create -y -n rsat -c bioconda -c conda-forge "rsat-core=2026.10.08"
  ./bin/micromamba clean --all -y
  echo "STAGE python start"
  python3 -m pip install --break-system-packages "pyranges<1" pyfaidx biopython itables session-info pyyaml nbformat nbclient ipykernel jupyter-client cairosvg "quarto-cli==1.11.9"
  echo "STAGE rsat done"
' > /home/claude/rsat_install.log 2>&1 &
export RSAT_ENV=/home/claude/mm/root/envs/rsat
```

A few minutes; the user hears about it from the messages described under
*Keeping the user informed*.

The pin matters twice over. It skips a fresh dependency solve, and it makes every
session install the same RSAT; the committed scan was reproduced exactly on
`2026.10.08`. Change the pin deliberately, and re-check that the scan still
reproduces, not as a side effect of an install. The `clean` at the end returns
the package cache's disk space.

`biopython` is not optional: `pyfaidx` refuses to open a bgzipped FASTA without
it, raising *BioPython >= 1.73 must be installed to read block gzip files*, and
the genome is bgzipped. It is installed by the job above, before any extraction.

Quarto comes from PyPI (`quarto-cli`, pinned to `1.11.9`) because it installs and
runs with nothing else to fix; the conda-forge package did not run until its
bundled tools were linked by hand. It takes about 420 MB on disk and about half a
minute to install. The notebook needs Quarto's own Jupyter packages, which the
same line installs.

`cairosvg` is also not optional if a presentation change is requested:
`restyle_sitemap.py` (section 5b) needs it to regenerate PNG and PDF from an
edited SVG. Without it the script still edits the SVG but leaves the PNG and
PDF as they were, which then disagree with it.

**Never put the RSAT environment on `PATH`, and never `micromamba activate rsat`.**
It ships its own `python3`, which has none of the packages above and silently
shadows the system one; a test run lost time to exactly that. Use `RSAT_ENV` as
shown. `motifscan.RSAT` and the notebook build a private `PATH` for the RSAT
subprocesses only. Call `python3 -m pip` and `python3 …`, never bare `pip` or
`python`.

### 3b. Fetch and verify the genome

Run the repository's own scripts; do not improvise a download. Run them
detached, from the clone, in this order:

```bash
cd /home/claude/dna032
setsid nohup bash -c '
  set -e
  echo "STAGE genome start"
  bash .claude/skills/ft-motif-search-skill/scripts/fetch_genome.sh
  echo "STAGE genome verify"
  python .claude/skills/ft-motif-search-skill/scripts/check_genome.py \
      Data/ncbi_dataset_RefSeq_GCF_000001635.27
  echo "STAGE genome filter"
  python .claude/skills/ft-motif-search-skill/scripts/prefilter_gff.py \
      Data/ncbi_dataset_RefSeq_GCF_000001635.27/genomic.gff.gz
  echo "STAGE genome done"
' > /home/claude/genome_fetch.log 2>&1 &
```

About 900 MB and ten minutes on a fresh session; say so rather than going
quiet. The files stay bgzipped — do not decompress them, there is not enough
disk for that and the `.fai`/`.gzi` indexes make it unnecessary. If
`check_genome.py` fails, the job stops there (`set -e`) and there is no
`STAGE genome done` line: let it refuse and fetch again; never scan against a
genome that did not verify.

`prefilter_gff.py` is not optional here. Parsing the full 920 MB GFF needs
~11 GB of RAM and is OOM-killed in a chat sandbox; the script writes the
RefSeq Select mRNA records (~6 MB) that the notebook reads instead, with
identical results. Do not hand-filter the GFF or edit the notebook's GFF path —
that was the workaround this step replaces, and it is now a deviation.

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

Write outputs to `/home/claude/runs/<timestamp>/`, never into the clone. Run the
notebook copy as the repository skill's step 7 says, with these set:

```bash
cd /home/claude/runs/<timestamp>
DNA032_RESULTS="$PWD" DNA032_PROJECT=/home/claude/dna032 QUARTO_PYTHON="$(command -v python3)" \
    quarto render notebook.ipynb --to html --execute --output notebook_report.html
```

`DNA032_RESULTS` keeps the outputs out of the clone's `Results/`. `DNA032_PROJECT`
is needed because the run directory is outside the clone; without it the
notebook falls back to a path on the maintainer's server.

**Execute the notebook with `quarto render`, once, and nothing else.** Never use
nbclient, papermill or `jupyter nbconvert --execute`. The notebook's last cell is
only skipped by Quarto (`eval: false`); any other executor runs it, and it then
renders the **committed** notebook, re-running the default panel (37 genes, 5 kb)
over the run's outputs and modifying a tracked file. That happened in a test run.

If the clone does change, do not repair it with `git checkout`, `restore`,
`reset` or `stash`: they are forbidden. The clone is disposable here. Discard it,
clone again, and redo the run.

Build the zip **only** with the repository's `package_results.py` (step 9 of
the repository `SKILL.md`):

```bash
python /home/claude/dna032/.claude/skills/ft-motif-search-skill/scripts/package_results.py \
    /home/claude/runs/<timestamp>
```

It first runs `verify_run.py`, which compares what the run produced with the
genes, window, p-value and motifs recorded in the run's own `run_config.yaml`
and checks the repository is unchanged; a failure there means the run is wrong
even though every file is present, so do not zip it anyway. Show its lines in
the reply. It then refuses to build a zip that is missing any required file and
names what is absent. If it refuses, produce the missing files and run it again —
never zip files by hand, and never call a partial zip complete. Present the report and
the site map as files, the site map on its own as well as inside the zip, and
show the script's `OK` output (zip path and file list) in the reply.

### 5b. Changing how the results look

The line is **analysis versus presentation**.

**The analysis is never touched.** That is where a motif lies in the promoter —
the site positions, strands, scores and p-values, which are the result itself —
and everything that produces them: the promoter extraction, the matrix
conversion, the RSAT calls and every parameter in them, and the hit table. It
also includes what marker size means: size must keep growing with significance
(a smaller p-value gives a larger marker), and that mapping is not changed. A
locked parameter stays refused; nothing in this section turns a refusal into
permission. A request to move a site or change what marker size means is
refused exactly like a locked analysis setting, and recorded the same way: in
`requested_changes.md`'s "Refused or not possible" section, naming which of
the two it would have touched.

**Everything else visual may be changed**, including scaling. That covers marker
shape, colour, font weight and size, labels, title, legend, figure size and
layout, the order of the promoter lanes, and making all markers or all text
larger or smaller together. `runconfig.py` exposes only some of these, and the
notebook does not read all of the ones it exposes.

**Use `scripts/restyle_sitemap.py` first**, on the already-rendered
`sitemap_*.svg` in the run directory:

```bash
python /home/claude/dna032/.claude/skills/ft-motif-search-skill/scripts/restyle_sitemap.py \
    /home/claude/runs/<timestamp>/matrix_scan/sitemap_<name>.svg \
    --recolor Spic=#1B9E77 --hide-gene Sqstm1 --set-text title="Nrf2 network" --bold title \
    --log /home/claude/runs/<timestamp>/requested_changes.md
```

It recolours a motif, hides a gene's lane, edits the title or a label's text,
sets font-weight or font-size, and swaps a marker's shape -- each new shape
sized from that marker's own existing bounding box, so a point that was bigger
because it was more significant stays exactly as big. It never writes a
coordinate, checks that itself before writing anything, and refuses (nothing
written) if a requested gene or motif is not in the figure. It then
regenerates the PNG and PDF from the edited SVG (needs `cairosvg`, installed in
step 3) so all three formats in the zip agree. With `--log`, it also writes its
own "Applied" entry into `requested_changes.md` (section 6) from what it
actually changed -- do not describe the same edit yourself.

For a visual change it does not support (figure size, layout, promoter sort
order, a new kind of element), edit the **figure-drawing code of the notebook
copy in the run directory** instead, then run that copy again with
`quarto render`, so the figure and the report still come from the same
notebook. The clone stays untouched either way. Do not redraw a figure outside
the notebook or `restyle_sitemap.py`, and do not edit an output by hand.

There is no equivalent self-check for this path -- the figure-drawing code can
do anything, and nothing here tries to constrain what kind of visual edit it
makes. What keeps the boundary real is narrower: the edit stays inside the
figure-drawing cell, never the analysis cells (where `hits`, `lim`, `tss_pos`
or anything upstream of them is computed), and the entry in
`requested_changes.md` is **the new cell's actual code**, pasted in full as a
fenced code block, not a prose description of it -- so a reader can check for
themselves that nothing in it computes a position. Name the cell or function
changed, alongside the code.

The repository skill carries the same rule. If an older clone's text seems to
say otherwise, this is the newer rule for presentation.

If the requested change would remove information the figure carries, say so
once and offer a way to keep it. Circles instead of triangles, for example, drop
the strand, which the triangles show by pointing up or down; filled and open
circles, or an added strand column, would keep it. Then do what the user decides.

### 6. Record what the user asked to change

The four questions and their defaults are this skill's own. Anything else the
user asks for goes in `requested_changes.md` in the run directory: a different
colour or title, an extra output, a change of wording, a request to alter a
locked parameter, anything outside the four choices. The user can hand the file
to the maintainer (**sara.salazar@gimm.pt**), so a request is never lost
inside a chat, and the file shows what was done by default and what was asked.

For a visual change applied with `restyle_sitemap.py --log`, the script writes
its own "Applied" entry from what it actually changed -- do not also describe
it yourself. Add everything else by hand: a change made by editing the
notebook copy instead, a refusal, or anything not possible here.

Do not log the answers to the four questions; `my_settings.yaml` and
`run_config.yaml` already hold those. Do not log your own suggestions as the
user's requests. If you suggested something and the user accepted it, record it
as *suggested by the agent, accepted*.

Write one entry per request, in the user's own words, with what was done and a
status: **applied**, **refused** (locked), **not possible here**, or **needs the
maintainer**. For a refusal, give the setting's name and relay the message from
`runconfig.py` as it was shown.

```markdown
# Requested changes — run <timestamp>

Run <timestamp> · repository commit <short hash> · skill <version>

## Applied
- "<what the user asked>" → <what was done> (setting: figure.width_in = 12)

## Refused or not possible
- "<what the user asked>" → <reason>. Locked: <setting>. Contact sara.salazar@gimm.pt.

## For the maintainer
- "<what the user asked>" → needs a code or method change, not a setting
```

Write the file on **every** run. When nothing was asked, it says *No changes
requested beyond the four choices.* A missing file cannot be told apart from a
forgotten one.

Write it **before** the zip is built in step 5. `package_results.py` lists it in
its contract and refuses to build without it, so it travels inside the zip.
Also return it to the user as its own file, next to the site map.

Check that the script's `OK` output lists `requested_changes.md`. If it does
not, the clone predates that contract line: say so, deliver the file beside the
zip instead, and do not add it to the zip by hand or edit the script.

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
- [ ] RSAT (pinned to `rsat-core=2026.10.08`) and the genome fetch started detached right after the clone, in parallel, with the four questions asked while they ran; each job followed through its log, and the scan did not start until both showed `done` and the genome check had passed
- [ ] `biopython` installed before any attempt to read a bgzipped FASTA with `pyfaidx`
- [ ] The RSAT environment was never put on `PATH` or activated; `python3 -m pip` and `python3` were used throughout
- [ ] Genome fetched and verified with `fetch_genome.sh` and `check_genome.py` before any extraction, and the user told the first fetch was running rather than left waiting in silence
- [ ] `prefilter_gff.py` run after the check, and the notebook copy changed only in its parameter cell and, where the user asked for a visual change not handled by `restyle_sitemap.py`, in its figure-drawing code — never in the analysis cells — with the new cell's actual code (not a description of it) recorded in `requested_changes.md` (the report names `genomic.refseq_select_mrna.gff` as the annotation read)
- [ ] Promoters re-extracted in this run from the fetched genome; the committed FASTA was used only if the genome could not be fetched, and that reuse was disclosed in the answer and in the report
- [ ] All four choices taken from the user — motifs, genes, upstream window, p-value — and the window and threshold reported, flagged where not 2 kb and 1e-4
- [ ] Every requested gene present in the scanned set; a missing gene stopped the run rather than being scanned around
- [ ] Outputs written to `/home/claude/runs/<timestamp>/` (notebook run with `DNA032_RESULTS` set to it), nothing written into the clone
- [ ] Before each stage the user was told what was starting and whether it takes time; stages that can exceed a minute ran in the background and were checked in rounds of at most 4 minutes, with a message after each round; no single command ran past 300 seconds
- [ ] Notebook executed once, by `quarto render` only, with `DNA032_RESULTS` and `DNA032_PROJECT` set; if the clone changed it was discarded and cloned again, not repaired with git
- [ ] `verify_run.py` passed, and its lines were shown in the reply, or its failures were reported to the user
- [ ] Zip built by `package_results.py`, not by hand, and its `OK` output shown in the reply
- [ ] `requested_changes.md` written in the run directory on this run (even if empty of requests), every request outside the four choices logged with its outcome, refusals naming the locked setting and the maintainer's address, written before the zip was built, listed in `package_results.py`'s `OK` output (or, if the script did not list it, the user told it is delivered beside the zip), and also returned to the user as its own file
- [ ] No genome, API or sequence source substituted for the ones the repository specifies

---

## If asked to change the skill itself

Changes belong in the repository, not here. Propose a diff and tell the user to
apply it in their checkout and commit it. An edit to the clone disappears when
the session ends.
