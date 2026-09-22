# Software literature search

Moved into this repository on 2026-09-21 (MIGRATION_PLAN step 4b). The three layers now
live at `data/lit-search/raw/`, `data/lit-search/decisions/` and `results/lit-search/`;
`paths.py` is where that is written down, and the only file the move needed.

The structured, reproducible search behind Appendix S1
(`manuscript/supplementary/S1-software-landscape.tex`), the comparison in Table 1, and the
candidate register (`results/lit-search/software-candidate-register.xlsx`).

```bash
python3 -m manuscript_analysis.lit_search           # screen, audit, register, counts
python3 -m manuscript_analysis.lit_search --check   # also verify the manuscript
```

Runs from any directory. Python 3, standard library only, plus `openpyxl` for the register.

## Three kinds of file, one rule each

This is the whole organising idea. The previous layout mixed all three in one directory,
so "which of these can I safely delete?" had no answer.

| directory | written by | safe to delete |
|---|---|---|
| `data/` | **nobody.** It is the evidence. | no |
| `decisions/` | **a human, by hand.** No script ever writes here. | no |
| `results/` | **the scripts, only.** | **yes, always** — a re-run rebuilds it |

## Layout

```
__main__.py              the one entry point
queries-as-executed.md       the verbatim queries, filters, dates and result counts
refactor-plan-v01.md     how this directory got here and what is left
table-rows-proposal-v01.md  how Table 1's rows were settled, and what is still open

../../../../data/lit-search/raw/        the archived search exports, 2026-07-15
  pubmed-metadata.csv      2,403 records: PMID, title, journal, year, DOI
  pubmed-abstracts.txt     2,364 records with abstracts (MEDLINE text)
  lens-export.csv          1,009 records: journal, conference and preprint

  paths.py                 where everything lives; the three-layer rule, in code
  lexicon.py               THE canonical term sets. One lexicon, every source.
  screen.py                the pre-filter; joins decisions/ onto the shortlists
  recall.py                the three-part audit of the set-aside records
  register.py              formats decisions/ into the register workbook
  report.py                counts.json, lexicon prose, and the appendix check
  tables.py                verifies the worksheet's bib keys and DOIs against the bibliography
  table1_tex.py            projects Table 1 from the worksheet into results/, with a drift check
  validate_decisions.py    checks screen-decisions.csv and the register against the codebook
  prisma.py                generates the PRISMA flow from counts.json + the register
  manifest.py              checksums data/ and results/; alarms if data/ ever changes
  seed_decisions.py        one-off: built decisions/screen-decisions.csv

../../../../data/lit-search/decisions/  hand-maintained. See its own README.
  screen-decisions.csv     645 advanced records; decision + reason
  screen-decisions-codebook.md  what every column means and what may go in it
  table-marks.csv          14 packages x 11 capabilities; THE source of truth for marks
  table-notes.csv          one row per justified cell; the reason behind every * mark
  packages.csv             the register's 56 package rows
  cran-taskview.csv        the register's 34 CRAN task-view rows

../../../../results/lit-search/         generated
  shortlist-pubmed.csv  shortlist-lens.csv     advanced by the pre-filter
  dropped-pubmed.csv    dropped-lens.csv       set aside
  recall-nearmiss.csv  recall-titlesweep.csv  recall-sample.csv
  counts.json              every number the appendix quotes
  prisma-flow.mermaid  prisma-flow.html   Figure S1, generated
  MANIFEST.sha256          sha256 of every file in data/ and results/
  table-1-maintext.tex     Table 1 as LaTeX, generated from decisions/table-marks.csv
  lexicon-prose.txt        the §S1.1 term listing, generated from lexicon.py

old/                     the superseded first pass; see its README
```

## What the pipeline does

The lexicon is defined **once** in `src/lexicon.py` and applied unchanged to both sources,
which is what §S1.1 reports. A record advances iff all three concept blocks fire in its
title, abstract or keywords.

```
PubMed   2,403 retrieved → 2,364 with abstracts screened →   437 advanced, 1,927 set aside
Lens     1,009 retrieved → 340 PubMed duplicates → 669 novel → 208 advanced,   461 set aside
TOTAL                                              3,033 screened → 645 advanced
```

The 2,388 set-aside records then get a three-part recall audit: a near-miss stratum (empty
by construction), an exhaustive package-title sweep (101, all out of scope), and a seeded
random sample of 100 from the 1,585 with no title cue (zero misses).

Reproduce any of it by re-running the pipeline; the numbers above are regenerated into
`results/counts.json` on every run.

## `--check`

Eight assertions, all of which pass today:

1. **The appendix's numbers match the pipeline.** 14 counts pulled out of the live
   `S1-software-landscape.tex` by the phrase that carries them and compared against
   `counts.json`. This is the guarantee the whole pipeline exists to provide: a number
   cannot drift between the analysis and the paper without the check failing.
2. **Appendix S1.3 lists every term the screen runs on**, in both directions, so the
   reported protocol and the executed screen cannot diverge.
3. **Every disposition is present**: all 645 advanced records carry a decision and a reason.
4. **The decision vocabularies hold**, in `screen-decisions.csv` and in the register, against
   the lists in `screen-decisions-codebook.md`, which the validator reads rather than
   duplicates.
5. **Every citation resolves**: each package's `bib_key` is in `references.bib` and the DOI
   beside it matches.
6. **Table 1 is a projection of the worksheet**, cell for cell, under documented rules for
   how a `*` resolves.
7. **The register rebuilds** from the decisions with no change to any existing value.
8. **The archived exports have not changed**, by checksum against the previous run. They
   cannot be re-fetched, so this is the one that protects everything above it.

## Two things to know before editing

**Never hand-edit the register workbook.** `register.py` rewrites it from
`decisions/packages.csv` and `decisions/cran-taskview.csv`. Edit those.

**Re-running never destroys a decision.** `screen.py` joins `decisions/screen-decisions.csv`
on and cannot write to it, and the seeding scripts refuse to overwrite an existing file. It
was not always so: before 2026-09-19 the shortlists carried `decision` columns that a re-run
would have silently blanked.

## Provenance

`queries-as-executed.md` has the verbatim Lens query and filters, and the PubMed query, which was
reconstructed and then **verified to return 100% of the 2,403 archived PMIDs**. Registry and
citation-chaining sources are discovery rather than counted retrieval and are reported in
§S1.8 by the packages they surfaced.

The July 2026 first pass, which inadvertently ran three different lexicons, is archived in
`old/` with a README explaining what changed. Nothing there feeds the current results.

_Restructured 2026-09-19. Every output verified identical to the pre-restructure pipeline._
