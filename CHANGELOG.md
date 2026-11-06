# CHANGELOG — FT Motif Search (DNA_032)

Tracks what changed in the SOP, the two skills, the scripts and the README, and
**who asked for it**. Reconstructed from the working conversation up to
6 November 2026; correct any entry that is wrong.

## How to read this file

Every change carries one of these tags:

| Tag | Meaning |
|---|---|
| **USER** | You asked for it, decided it, or made it yourself |
| **USER (accepted)** | The assistant suggested it and you said yes |
| **ASSISTANT** | Done on the assistant's own initiative, not asked for. Listed so it can be reviewed or reverted |

Within each date, **USER** entries come first and **ASSISTANT** entries are
grouped under their own heading, so the two never mix.

## Rules for adding entries

1. Add an entry **before** a change is delivered, not afterwards.
2. If a change was not asked for, tag it **ASSISTANT** and say why it was made.
3. The assistant proposes extras in words first and applies them only after you
   approve; an approved extra is re-tagged **USER (accepted)**.
4. The agent never edits this file (the repository is read-only to it). Entries
   are added by you, or handed over as lines to paste.

Entry format: `- **TAG** — what changed. *Files:* …`

---

## 2026-11-06

### Requested by the user

- **USER** — Boundary for visual changes, made exact: any visual change is allowed except (1) where a motif lies in the promoter, which is the result itself, and (2) what marker size means, since size must keep following the p-value. Making everything larger or smaller together is allowed. *Files:* chat skill step 5b (rewritten); repository skill (new paragraph and checklist item, delivered as `ft-motif-search-skill_SKILL.md` for you to apply).
- **USER (accepted)** — Faster setup: RSAT install and genome fetch started detached (`setsid nohup`) right after the clone, in parallel, while the four questions are asked; each job writes `STAGE` lines to its own log; `rsat-core` pinned to `2026.10.08` (the version the committed scan was reproduced on); package cache cleared after the install. *Files:* chat skill (new "Start the setup first" section, steps 3 and 3b, checklist).
- **USER** — The agent may change how results *look*, but never the analysis. The notebook copy in the run directory can have its figure-drawing code edited (marker shape, font weight, colours, labels); the promoter extraction, matrix conversion, RSAT calls and hit table cannot. The repository itself stays untouched, and every such edit is recorded in `requested_changes.md` and `run_log.md`. *Files:* chat skill (new step 5b, checklist). The repository skill still says "parameter cell only" and needs the same wording.
- **USER** — A test run asked for circles, bold lettering and a blue/orange palette. None was applied. `runconfig.py` has no marker shape or font weight, and the notebook builds its colour dict as a literal inside the matrices cell, so nothing reads `figure.colors`. Recorded in that run's `requested_changes.md`; the rule above is the outcome.
- **USER (accepted)** — `requested_changes.md` written on every run, and shipped inside the zip. One line added to `CONTRACT` in `package_results.py`; the skill writes the file before the zip and falls back to delivering it beside the zip if the script does not list it. *Files:* `package_results.py`, chat skill.
- **USER (accepted)** — Progress messages before, during and after each stage; long steps run in the background and are checked in rounds of at most 4 minutes (a single command is stopped at 300 seconds); a table of expected times. *Files:* chat skill.

### Not requested (assistant initiative)

- **ASSISTANT** — Correction: I said the repository skill restricts notebook edits to "the parameter cell". It does not; that wording was in the chat skill's checklist. What the repository skill lacked was the *how* for presentation changes the settings do not cover, which is what the agent needed to apply the circles. The rule is now written into both skills.
- **ASSISTANT** — Correction: the `CONTRACT` line first offered had a third `True` field, but the repository's entries have two fields, so it would have failed. Replaced with the two-field line before it was used. *Files:* `package_results.py`.

---

## 2026-11-03

### Requested by the user

- **USER** — Upstream promoter length has no upper limit; the 1 kb minimum stays. *Files:* `runconfig.py`, repository `SKILL.md`, README, SOP.
- **USER** — The genome, background model, pseudo-counts, downstream promoter length (200 bp) and strand handling stay locked, and only the upstream length is settable. *Files:* chat skill 0.5.1, SOP.
- **USER** — SOP "Where to run it" rewritten as two equivalent routes (chat or your own machine); the server section and the comparison table removed; chat can extract promoters for new genes. *Files:* SOP.
- **USER** — SOP: predicted site needs ChIP *plus* evidence of transcription change; RefSeq Select rationale (most consensual gene definition, not the isoform-rich annotation); "Confirm final results with a local run" in the contact section. *Files:* SOP.
- **USER** — SOP 1.4: zip holds the site map as SVG, PNG and PDF plus the run record; `run_log.md` description expanded; `package_results.py` named as the authority on the file list; closing-checklist sentence. *Files:* SOP.
- **USER** — SOP: release tag `genome-GRCm39-GCF_000001635.27` named, and the 6 MB `genomic.refseq_select_mrna.gff` paragraph (same transcripts, ~11 GB of memory avoided). "Most of it reading the annotation" became "most of it the motif scan itself". *Files:* SOP.
- **USER** — Markdown contents table added to the SOP, replacing the empty one. *Files:* `SOP.md`.
- **USER** — Chat skill copy kept in the repository for safekeeping. *Files:* `docs/chat-skill/motif-scan-from-github/SKILL.md`.
- **USER** — Made on your side, seen in the uploaded files: `prefilter_gff.py` step and checklist item, `DNA032_RESULTS` environment variable, `package_results.py` wired in as step 9, version bumps. *Files:* repository `SKILL.md`, chat skill.

### Not requested (assistant initiative)

- **ASSISTANT** — Rebuilt the whole SOP Word file from `SOP.md` with a generator instead of patching it. Reason: the Word had drifted from the markdown and still said "between 1,000 and 10,000 bp". This also changed eleven passages you had not asked about (wording now matches your markdown). *Files:* `SOP_FT_Motif_Search.docx`, `md2docx.js` (new, optional, delete if unwanted).
- **ASSISTANT** — `package_results.py`, which refuses to build an incomplete zip. Reason: a packaging cell bundled four files while the contract listed seven. You adopted it afterwards, so it is now **USER (accepted)**.

---

## 2026-11-02

### Requested by the user

- **USER** — Genome delivered as a GitHub release (bgzipped FASTA, GFF, `.fai`, `.gzi`, `SHA256SUMS`) instead of through git or NCBI. *Files:* release `genome-GRCm39-GCF_000001635.27`, `fetch_genome.sh`.
- **USER** — `fetch_genome.sh` keeps the genome compressed (906 MB, not 3.7 GB); `.fai` added to the release after the first run aborted on its absence. *Files:* `fetch_genome.sh`.
- **USER** — README updated: setup, the agent, settable versus locked, known issues, troubleshooting. *Files:* `README.md`.
- **USER** — Development record (revision 2, then 3) and SOP created as Word documents, with contact. *Files:* `FT_Motif_Search_development_record.docx`, `SOP_FT_Motif_Search.docx`.
- **USER** — Chat skill: repository URL hardcoded; asks motifs (selection boxes), then genes, then p-value, then waits. *Files:* chat skill.
- **USER** — A fourth question, promoter length, added to the gates. *Files:* repository `SKILL.md`, chat skill, SOP.

### Not requested (assistant initiative)

- **ASSISTANT** — Closing "Checklist before finishing" in both skills. You liked it when it was described and asked for it, so it is **USER (accepted)**.

---

## 2026-10-30

### Requested by the user

- **USER** — The chat-side skill: clone the repository from GitHub and run it there, as a single `SKILL.md`. *Files:* `motif-scan-from-github`.
- **USER** — Skill name made readable. You asked for `FT_Motif_Search_skill`; the validator only accepts lowercase and hyphens, so it became `ft-motif-search-skill`, with display name "FT Motif Search".
- **USER** — The agent must never modify the repository; every run writes to `runs/<timestamp>/`. *Files:* repository `SKILL.md`.
- **USER** — Settings file for what users may change (colours, size, formats, TFs, genes, p-value). Anything locked is refused with a message to contact sara.salazar@gimm.pt. A file records the user's changes so they can hand it back. *Files:* `runconfig.py`.
- **USER** — The reference genome is locked (species, accession, assembly, annotation release). *Files:* `runconfig.py`, `check_genome.py`.
- **USER** — Repository skill and chat skill kept as two skills, chat copy installed in the profile only. *Files:* skills layout.

### Not requested (assistant initiative)

- **ASSISTANT** — Exact gene matching in `select_promoters()`, replacing the substring test, and an error when a requested gene has no promoter. Disclosed at the time; you confirmed the published results were unaffected (`Cat` never returned `Cat1`) and the fix stayed in as insurance. *Files:* `motifscan.py`.
- **ASSISTANT** — Alias map in `runconfig.py` (`genome`, `assembly`, `build`, `markov`, `window`, …) so a near-miss key gets the real refusal instead of "unknown setting". *Files:* `runconfig.py`.
- **ASSISTANT** — `check_genome.py` also verifies the annotation release, not only file sizes. *Files:* `check_genome.py`.

---

## 2026-10-29

### Requested by the user

- **USER** — Never reuse what is already there: always recompute, never hand back an earlier result, and only run against the full genome. *Files:* repository `SKILL.md`.
- **USER** — Progress messages at every stage. *Files:* `SKILL.md`, `motifscan.py`.
- **USER** — Gene gate: report genes not found, give UniProt links, ask for new names, re-test, only then continue. *Files:* `check_genes.py`, `SKILL.md`.
- **USER** — Ask for motifs first, in selection boxes, then genes, then p-value. *Files:* `SKILL.md`.
- **USER** — Only the four curated motifs for now (Spic, Nfe2l2_1, Nfe2l2_2, Bach1). *Files:* `SKILL.md`.
- **USER** — No Ensembl API: the reference must be the current RefSeq GRCm39 genome. Transcripts stay as the notebook handles them (all RefSeq Select records kept). *Files:* design decision.
- **USER** — Report and site map delivered as a zip, with the map also given on its own. *Files:* `SKILL.md`.

---

## Proposed by the assistant and not adopted

| Proposal | Outcome |
|---|---|
| Commit a small test fixture of promoters | Rejected: users must search any gene |
| Git LFS for the genome | Rejected: 2 GB per-file cap, bandwidth quota |
| `package_skill.sh` in the repository | Not needed for your workflow; left out |
| Ensembl REST for promoter windows | Rejected (see 2026-10-29) |

## Open, not yet decided

- `LICENSE` file for the public repository.
- Repository `SKILL.md` frontmatter still reads `0.2.0` and the chat skill `0.5.1` although both changed since; bump so the version signals something.
- ADA skill conventions: top-level `version`, a `references/` folder, a marked `CLAUDE.md` block.
- `pyranges.get_sequence()` against the bgzipped `.gz`: never run on its own.
- Notebook ignores `figure.colors`: the settable colours in `runconfig.py` have no effect. Marker shape and font weight are not in `runconfig.py` at all. Fix in the repository: have the notebook read the figure settings, and expose marker shape and font weight.
- Apply the delivered repository skill (`ft-motif-search-skill_SKILL.md`), so it carries the same analysis-versus-presentation rule as the chat skill. Until then the chat skill's step 5b says it is the newer rule.
- Time the stages in a real run (annotation filter, promoter extraction, report render) and put the numbers in the chat skill's expected-times table.
- A full user-style test run: new gene panel, non-default window and threshold, and an attempt to change a locked setting.
