# CHANGELOG — FT Motif Search (DNA_032)

Tracks what changed in the SOP, the two skills, the scripts and the README, and
**who asked for it**. Reconstructed from the working conversation up to
6 November 2026; correct any entry that is wrong.

## How to read this file

Every change carries one of these tags:

| Tag                       | Meaning                                                                                         |
| ------------------------- | ----------------------------------------------------------------------------------------------- |
| **USER**            | You asked for it, decided it, or made it yourself                                               |
| **USER (accepted)** | The assistant suggested it and you said yes                                                     |
| **ASSISTANT**       | Done on the assistant's own initiative, not asked for. Listed so it can be reviewed or reverted |

Within each date, **USER** entries come first and **ASSISTANT** entries are
grouped under their own heading, so the two never mix.

## Rules for adding entries

1. Add an entry **before** a change is delivered, not afterwards.
2. If a change was not asked for, tag it **ASSISTANT** and say why it was made.
3. The assistant proposes extras in words first and applies them only after you
   approve; an approved extra is re-tagged **USER (accepted)**.
4. The agent keeps this file and `SOP.md` in sync with every other change it
   makes in the repository, adding the changelog entry and updating the SOP's
   wording in the same pass, without being asked separately each time. This
   does not extend to the analysis notebook or scripts: those stay off-limits
   to an unasked edit, per each skill's own `SKILL.md`, regardless of this rule.

Entry format: `- **TAG** — what changed. *Files:* …`

---



## 2026-11-09

### Requested by the user

- **USER** — Both skills pinned to run on Sonnet (`model: sonnet` added to each `SKILL.md`'s frontmatter), to stop the harness defaulting this well-specified, existing-code workflow to a costlier model. *Files:* both skills. Version bumped to 0.9.0 to match (the commit that added the field did not bump it).

## 2026-11-07

### Requested by the user

- **USER** — The zip no longer logs out-of-scope requests. `requested_changes.md` removed entirely: dropped from the chat skill and from `package_results.py`'s CONTRACT. *Files:* `package_results.py`, chat skill.
- **USER** — Promoter window question: `2 kb` labeled `(Recommended)` everywhere (it already was in the repository skill; added to the chat skill), and "published" wording removed from that question's text. *Files:* both skills, `SOP.md`.
- **USER** — Presentation changes to the site map now go through a new `restyle_sitemap.py` instead of editing the notebook's figure code each time: recolour, hide a gene, edit text, bold, resize text, change marker shape, all on the rendered SVG, with PNG/PDF re-exported to match. *Files:* `restyle_sitemap.py` (new), the notebook (`sitemap()` now tags elements with `gid` and uses `svg.fonttype: none`), both skills.
- **USER** — SOP and both Word docs re-synced after a second session had, in parallel, updated them to the pre-removal `requested_changes.md` design; brought back in line with the state above, development record advanced to Revision 5. *Files:* `SOP.md`, `SOP_FT_Motif_Search.docx`, `FT_Motif_Search_development_record.docx`.
- **USER** — Reconsidered, same day: `requested_changes.md` is back — a register of everything asked beyond the four questions, including refused or disallowed requests, so it can be confirmed later that nothing applied affected the result. Rebuilt more robustly than the version removed above: `restyle_sitemap.py --log` now writes its own "Applied" entries from what it actually changed and verified unchanged, rather than the agent transcribing them from memory; everything else (refusals, notebook-copy edits) is still added by hand. Reinstated in `package_results.py`'s CONTRACT, both skills, `SOP.md` (now v1.7) and both Word docs (development record now Revision 6). *Files:* `restyle_sitemap.py`, `package_results.py`, both skills, `SOP.md`, `SOP_FT_Motif_Search.docx`, `FT_Motif_Search_development_record.docx`.
- **USER** — Clarified the boundary on notebook-copy figure edits (the fallback for visual changes `restyle_sitemap.py` can't make): no automated check is added for that path, and no new restriction on what the edit may contain, because constraining it to be machine-checkable would also constrain what visual changes are possible. The only rule stays what it was — edit the figure-drawing cell only, never the analysis cells — and the `requested_changes.md` entry for such an edit is now the cell's actual new code, pasted in full, so a reader can check it themselves instead of trusting a description. Marker-size-meaning confirmed to stay locked alongside position. *Files:* both skills, `SOP.md` (now v1.8), `FT_Motif_Search_development_record.docx` (Revision 6, closed out).
- **USER (accepted)** — Made explicit, in the analysis-versus-presentation boundary itself, that a request to move a site or change what marker size means is refused and recorded in `requested_changes.md`'s "Refused or not possible" section exactly like a locked analysis setting — this was already true via the general refusal instructions in step 7b/section 6, but wasn't stated at the point where the two rules are named, so an agent reading only that paragraph could miss it. *Files:* both skills.
- **USER** — `SOP.md`'s version scheme brought in line with both skills: `1.8` → `0.8`. The whole project is a prototype, and `1.x` was the only document still signalling otherwise. *Files:* `SOP.md`, `SOP_FT_Motif_Search.docx`.

### Not requested (assistant initiative)

- **ASSISTANT** — Final consistency pass before the user's own test: `README.md` had drifted out of sync with everything else this round — still listed three run-record files (missing `requested_changes.md`), said "2 kb default" instead of "(recommended)", never mentioned `restyle_sitemap.py`, and never showed the `--write-config` command for `run_config.yaml`. Updated to match. *Files:* `README.md`. Also removed three stale items from "Open, not yet decided" below: the version-bump note (both skills are now actively bumped each round), and two items confirmed already done by reading the actual files (the repository skill already carries the analysis-versus-presentation rule; the notebook's `render_report` guard is already committed).
- **ASSISTANT** — `run_config.yaml` was never actually produced by any documented command: `save_run_record()` existed in `runconfig.py` but had no CLI flag, so `verify_run.py`/`package_results.py` (which both require the file) could only be satisfied by calling the function directly in Python — an undocumented workaround, hit in the 2026-11-06 run. Added `runconfig.py --write-config RUN_DIR --settings PATH` and documented the call in step 7b. *Files:* `runconfig.py`, repository `SKILL.md`.

## 2026-11-06

### Requested by the user

- **USER (accepted)** — Three problems from a test run, fixed as I judged best (you said "implement if you think is best"): the RSAT environment's `python3` shadowing the system one; the notebook's last cell running under nbclient and rendering the committed notebook over the run; and nothing noticing that the outputs belonged to the default panel. See the entries below. *Files:* `verify_run.py`, `package_results.py`, `render_report_cell.py`, both skills.
- **USER** — SOP updated to 1.5 and the development record to revision 4, to match this round. SOP: any visual change within the analysis-versus-presentation boundary, the new troubleshooting rows, `requested_changes.md` in the results table and the zip, the stage messages and early setup, the check before packaging, and the owner receiving `requested_changes.md`. Record: the second incident, the shadowing python, the 300-second limit, presentation versus analysis, change tracking, a refreshed open-items table. *Files:* `.claude/skills/ft-motif-search-skill/docs/SOP.md`, `SOP_FT_Motif_Search.docx`, `FT_Motif_Search_development_record.docx`.
- **USER (accepted)** — `verify_run.py`, called by `package_results.py` before it zips: compares the promoters, hits table and raw scan with the genes, window, p-value and motifs in the run's own `run_config.yaml`, and checks the repository is unchanged (modified tracked files, or new files outside the run directory). Tested on the committed results with six wrong configurations and four repository states. *Files:* `verify_run.py` (new), `package_results.py`.
- **USER (accepted)** — Notebook `render_report` cell guarded: with `DNA032_RESULTS` set, it refuses to render when `NOTEBOOK_PATH` is the committed notebook. Interactive use is unaffected. *Files:* `render_report_cell.py`, to paste over cell 16 of the notebook.
- **USER (accepted)** — The notebook copy is executed with `quarto render`, once, and never with nbclient, papermill or nbconvert; the command sets `DNA032_RESULTS`, `DNA032_PROJECT` and `QUARTO_PYTHON`. Quarto is installed in chat from PyPI, pinned to `1.11.9`, together with its Jupyter packages. *Files:* both skills.
- **USER (accepted)** — Never put the RSAT environment on `PATH`; use `python3 -m pip` and `python3`. If the repository changed, discard the clone and clone again instead of repairing it with git. *Files:* both skills.
- **USER** — Boundary for visual changes, made exact: any visual change is allowed except (1) where a motif lies in the promoter, which is the result itself, and (2) what marker size means, since size must keep following the p-value. Making everything larger or smaller together is allowed. *Files:* chat skill step 5b (rewritten); repository skill (new paragraph and checklist item, delivered as `ft-motif-search-skill_SKILL.md` for you to apply).
- **USER (accepted)** — Faster setup: RSAT install and genome fetch started detached (`setsid nohup`) right after the clone, in parallel, while the four questions are asked; each job writes `STAGE` lines to its own log; `rsat-core` pinned to `2026.10.08` (the version the committed scan was reproduced on); package cache cleared after the install. *Files:* chat skill (new "Start the setup first" section, steps 3 and 3b, checklist).
- **USER** — The agent may change how results *look*, but never the analysis. The notebook copy in the run directory can have its figure-drawing code edited (marker shape, font weight, colours, labels); the promoter extraction, matrix conversion, RSAT calls and hit table cannot. The repository itself stays untouched, and every such edit is recorded in `requested_changes.md` and `run_log.md`. *Files:* chat skill (new step 5b, checklist). The repository skill still says "parameter cell only" and needs the same wording.
- **USER** — A test run asked for circles, bold lettering and a blue/orange palette. None was applied. `runconfig.py` has no marker shape or font weight, and the notebook builds its colour dict as a literal inside the matrices cell, so nothing reads `figure.colors`. Recorded in that run's `requested_changes.md`; the rule above is the outcome.
- **USER (accepted)** — `requested_changes.md` written on every run, and shipped inside the zip. One line added to `CONTRACT` in `package_results.py`; the skill writes the file before the zip and falls back to delivering it beside the zip if the script does not list it. *Files:* `package_results.py`, chat skill.
- **USER (accepted)** — Progress messages before, during and after each stage; long steps run in the background and are checked in rounds of at most 4 minutes (a single command is stopped at 300 seconds); a table of expected times. *Files:* chat skill.

### Not requested (assistant initiative)

- **ASSISTANT** — Design change, yours to veto: the report is now built once, in step 7, by the same `quarto render` that runs the analysis. Step 9 no longer renders again, and a "no" to the zip now means "do not package" rather than "do not render". Reason: the old design executed the whole analysis twice, once by whatever executor the agent picked and once by Quarto. *Files:* repository skill steps 7 to 9, chat skill.
- **ASSISTANT** — Correction: revision 3 of the development record lacked the section on the run log and the closing checklists that I said I had added. The heading I anchored the edit to did not exist and the replacement failed silently; the section is now there. I also removed rows in its open-items table that were stale (the NCBI API route, "three gates", the 0.2.0 version note, `biopython`).
- **ASSISTANT** — Layout fix in `md2docx.js`: the first column of a table is now wide enough for file names such as `requested_changes.md`, which were breaking mid-word.
- **ASSISTANT** — Correction to my diagnosis: nbclient ignoring `eval: false` was only half of it. The notebook finds itself by its long file name, the skill names the copy `notebook.ipynb`, so `NOTEBOOK_PATH` fell back to the committed notebook. Both halves are now closed.
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

| Proposal                                 | Outcome                                      |
| ---------------------------------------- | -------------------------------------------- |
| Commit a small test fixture of promoters | Rejected: users must search any gene         |
| Git LFS for the genome                   | Rejected: 2 GB per-file cap, bandwidth quota |
| `package_skill.sh` in the repository   | Not needed for your workflow; left out       |
| Ensembl REST for promoter windows        | Rejected (see 2026-10-29)                    |

## Open, not yet decided

- `LICENSE` file for the public repository.
- ADA skill conventions: top-level `version` (both skills still nest it under `metadata`), a `references/` folder, a marked `CLAUDE.md` block.
- `pyranges.get_sequence()` against the bgzipped `.gz`: never run on its own.
- Time the stages in a real run (annotation filter, promoter extraction, report render) and put the numbers in the chat skill's expected-times table. Only the Quarto install is measured so far (33 s).
- Disk in a fresh sandbox: the RSAT environment measured 3.7 GB here and Quarto 420 MB, more than the roughly 3 GB `df` reported at the start, yet everything installed, so `df` is not a reliable budget. Watch for a disk error in a fresh run.
- A full user-style test run: new gene panel, non-default window and threshold, and an attempt to change a locked setting.
