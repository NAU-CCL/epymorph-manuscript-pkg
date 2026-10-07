"""
Where everything lives, resolved relative to this file rather than the shell's cwd, so a
script works from any directory.

The three-layer rule the pipeline is built on is stated once, here, and the repository layout
now mirrors it:

    data/lit-search/raw/        the archived search exports. NEVER written.
    data/lit-search/decisions/  hand-maintained. Never written by a script.
    results/lit-search/         generated. Always safe to delete; the driver rebuilds it.

Moved here from the standalone `software-lit-search/` directory on 2026-09-21
(MIGRATION_PLAN step 4b). This file is the only one the move required: everything else
imports its locations from here.
"""
from pathlib import Path

# .../analysis/src/manuscript_analysis/lit_search/paths.py -> the repository root.
ROOT = Path(__file__).resolve().parents[4]

DATA = ROOT / "data" / "lit-search" / "raw"
DECISIONS = ROOT / "data" / "lit-search" / "decisions"
RESULTS = ROOT / "results" / "lit-search"

# Inputs: the three archived search exports. `queries-as-executed.md`, beside them, records
# the platform-specific query, field scope and filters that produced each one.
PUBMED_METADATA = DATA / "pubmed-metadata.csv"
PUBMED_ABSTRACTS = DATA / "pubmed-abstracts.txt"
LENS_EXPORT = DATA / "lens-export.csv"

# Hand-maintained. `screen-decisions-codebook.md`, beside them, defines every column and the
# vocabularies, and `validate_decisions.py` holds the files to it.
SCREEN_DECISIONS = DECISIONS / "screen-decisions.csv"
PACKAGES = DECISIONS / "packages.csv"
CRAN_TASKVIEW = DECISIONS / "cran-taskview.csv"
TABLE_MARKS = DECISIONS / "table-marks.csv"

# Generated.
SHORTLIST_PUBMED = RESULTS / "shortlist-pubmed.csv"
SHORTLIST_LENS = RESULTS / "shortlist-lens.csv"
DROPPED_PUBMED = RESULTS / "dropped-pubmed.csv"
DROPPED_LENS = RESULTS / "dropped-lens.csv"
RECALL_NEARMISS = RESULTS / "recall-nearmiss.csv"
RECALL_TITLESWEEP = RESULTS / "recall-titlesweep.csv"
RECALL_SAMPLE = RESULTS / "recall-sample.csv"
COUNTS = RESULTS / "counts.json"
LEXICON_PROSE = RESULTS / "lexicon-prose.txt"
TABLE1_TEX = RESULTS / "table-1-maintext.tex"
TABLE_S1_TEX = RESULTS / "table-s1.tex"
REGISTER_XLSX = RESULTS / "software-candidate-register.xlsx"

# The manuscript, now in the same repository. One bibliography: `references.bib` is what the
# LaTeX cites and what the worksheet's DOIs are checked against, so there is no second copy
# to keep in step. `manuscript/` here is mirrored to the `epymorph_ms_overleaf` clone that
# round-trips with the Overleaf editor; the two are kept byte-identical.
MANUSCRIPT = ROOT / "manuscript"
BIB = MANUSCRIPT / "references.bib"
APPENDIX = MANUSCRIPT / "supplementary" / "S1-software-landscape.tex"
INTRO = MANUSCRIPT / "sections" / "01-introduction.tex"
# The Methods summary of the search; it quotes the headline counts, so --check reads it too.
METHODS_SURVEY = MANUSCRIPT / "sections" / "04b-methods-software-survey.tex"

BOM = "﻿"
"""Written at the head of every CSV so Excel and Numbers read the UTF-8 correctly."""
