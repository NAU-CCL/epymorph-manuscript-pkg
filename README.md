# epymorph-manuscript-pkg

Reproducibility package for the epymorph manuscript: data, analysis code and manuscript
source in one repository with one git history, following FAIR4RS principles.

The goal it is built to: **nothing in the manuscript asserts a number the code cannot
reproduce.** Every figure, table and quoted count is generated, and `just check`
fails if any of them stops agreeing with the code that produces it.

The layout is meant to be generic. Any future project of "a Python analysis plus a
manuscript" could reuse it.

---

## How this repository works

Four layers, and **what writes a file decides where it lives.** That one rule explains
every directory here.

| | written by | in git | safe to delete |
|---|---|---|---|
| `data/` | nobody. Archived evidence, never modified. | yes | **no** |
| `analysis/` | a human, editing code | yes | no |
| `manuscript/` | a human, via Overleaf | yes | no |
| `results/` | the scripts, only | mostly (see below) | **yes** — rebuilt |

`results/` is the one that matters in practice: if you are unsure whether a file is
precious, ask whether a script wrote it. Everything under `results/` can be deleted and
rebuilt, so nothing there should ever be hand-edited.

### The exception: the ensembles

`results/demos/runs/` is 1.02 GB of forecast ensembles across 318 files, one of them
114 MB, so **git does not carry it**. It is the only generated thing that cannot be
rebuilt on a whim: regenerating takes 8-10 hours. See `results/demos/README.md` for how
to regenerate or fetch it, and what the checksum manifest beside it means.

Everything needed to *check the paper* is in git without it: the figures, the tables, and
the frozen observations they were computed from.

---

## The workflow

### 1. Set up, once

```bash
just setup                    # uv sync, in analysis/
```

The recipes are in the `justfile` ([just](https://just.systems): `brew install just`); each
is one or two commands, readable there if you would rather not install it. No API key is needed to build or check anything. Every external input is frozen in the
repository: the CDC surveillance series in `data/demos/` (they are revised weekly, so
re-fetching would move the target the models are scored against), and the Census
demography, commuting and contact-matrix inputs in `data/raw/`, each with a provenance
record. epymorph downloads Census TIGER geography once per machine, which needs no key.

A free Census API key, in a `.env` copied from `.env.example`, is needed only to refresh a
frozen input deliberately, or to run the `01` notebooks, which fetch live to show how.

### 2. Build everything the manuscript uses

```bash
just build                    # minutes with the runs on disk; about 5 h without them
```

Runs the literature search, then each demo's notebook through papermill. A run already on
disk is reused and a missing one is fitted, so on a fresh clone this is the slow half of
the analysis; an interrupted build resumes rather than starting over. To skip it, fetch the
archived runs first (see `results/demos/README.md`).

Writes `results/lit-search/`, `results/demos/figures/` (six figures),
`results/demos/tables/` (six tables, each as a `.csv` to read and a `.tex` to `\input`),
the executed notebooks `results/demos/demo-*.ipynb`, and `results/checksums.sha256`.

### 3. Check it

```bash
just check                    # about 3 minutes
```

Self-contained checks, each regenerating something and comparing it against what is
committed: every generated `.tex` still carries its `% GENERATED` header; the
literature-search pipeline's own eight assertions; the demo tables against a fresh
generation, byte for byte; the demo figures against a fresh build, pixel for pixel (within
1-2/255 of antialiasing noise, which matplotlib's drawing carries from one process to the
next); every generated file against `results/checksums.sha256`, and the run outputs against
`results/demos/runs.sha256`. The demo checks are skipped, with a
message, when the run outputs are absent.

### 4. Publish the generated files to Overleaf

```bash
just publish                  # report
just publish --apply          # copy, then verify
```

Then, in the Overleaf clone: `git add -A && git commit && git push`, and click **Pull**
in Overleaf's GitHub panel.

### 5. Explore, if you want to

```bash
just notebooks
```

Each demo is one notebook, `analysis/manuscript_analysis/demo-flu.ipynb` and
`demo-covid.ipynb`, read top to bottom: it builds the models, explains one fit and
forecast, makes the runs, and scores them into the figures and tables. Opened
interactively it shows its figures and tables without writing them.

---

## What is here

```
data/
  demos/{flu,covid}/observations.csv   frozen surveillance. Cannot be re-derived.
  lit-search/raw/                      archived search exports
  lit-search/decisions/                hand-entered screening calls
analysis/
  pyproject.toml                       one uv environment
  manuscript_analysis/
    __main__.py                        the build: the search, then each demo notebook
    demo-flu.ipynb, demo-covid.ipynb   the two vignettes, top to bottom
    *_inputs.py, runs.py, scoring.py, plots.py, util.py   what they use that is not epymorph
    lit_search/     the software-landscape search pipeline
manuscript/         LaTeX, one file per section; round-trips with Overleaf
results/            organised by producer, mirroring data/
  demos/figures/    the manuscript's figures
  demos/tables/     the manuscript's tables, .csv and .tex
  demos/runs/       the runs. NOT in git; runs.sha256 beside it is
  checksums.sha256  everything else the build writes
  lit-search/       shortlists, register, PRISMA flow, Table 1
scripts/            check.py, sync-manuscript.sh, publish-results.sh, build-docx.sh
justfile            setup, build, check, notebooks, publish, ...
```

Each subdirectory has its own README with the detail.

### The two analyses

**The software landscape** (`lit_search`) surveys comparable packages. It arrived
2026-09-21 and was the first piece here that ran end to end; it is the working model for
everything else. Its step of `just check` regenerates
`results/lit-search/` and then checks eight things, including that Appendix S1's fourteen
quoted counts match the pipeline, that §S1.3 lists every term the screen runs on, that
Table 1 is a faithful projection of the decisions behind it, and that the archived exports
have not changed since the last run.

**The demonstration vignettes** (`demos`) arrived 2026-09-22. Both ask the same question
of different added structure -- *does it buy forecast skill?* -- with Demo 1 asking it of
demographic structure and Demo 2 of spatial structure and movement. Within each demo the
three models differ only in data, never in code, which is the claim the manuscript rests
on.

---

## Keeping the manuscript in step

The manuscript is edited in Overleaf, which round-trips with the separate
`epymorph_ms_overleaf` repository. `scripts/sync-manuscript.sh` mirrors it one way into
`manuscript/` here: it reports by default, copies with `--apply`, verifies byte-equality
afterwards, and refuses when a file is newer here than in Overleaf.

Generated figures, tables and numbers travel the other way, via
`scripts/publish-results.sh`.

**The two scripts are not a bidirectional sync.** They are two one-way mirrors over
**disjoint sets of files**, which is what makes the arrangement safe:

| | written by | direction |
|---|---|---|
| `main.tex`, `supplement.tex`, `sections/`, `supplementary/`, `references.bib` | a human, in Overleaf | Overleaf -> here |
| `figures/`, `tables/`, `manuscript-numbers.tex` | this repository's scripts | here -> Overleaf |

No file is ever written by both sides, so neither script can lose an edit the other made.
`publish-results.sh` additionally warns when a generated `.tex` in Overleaf has lost its
`% GENERATED` header, which is what a hand-edit looks like from the outside.

**Never hand-edit a generated table**, in either repository; `just check` catches it
here, and the publish script's warning catches it there.

The manuscript includes them the usual way:

```latex
\graphicspath{{figures/}}
\includegraphics[width=\textwidth]{fig2-flu-demographic-structure}
\input{tables/flu-skill}
```

---

## Still to come

- Referencing the generated figures and tables from the LaTeX: they are published into
  Overleaf but nothing `\input`s them yet.
- `scripts/build.sh`: the whole chain, analysis through to a compiled PDF, plus the
  "flatten to one file" step Springer Nature's submission format wants.
- `results/manuscript-numbers.tex`: generated `\newcommand` macros so prose quotes
  numbers rather than typing them.
- Porting real prose into `manuscript/`, which still holds the placeholder scaffold.
- An archive for the ensembles, and containerization.

See `MIGRATION_PLAN.md` in the working folder for the full plan and its history.

---

## License

Two licenses, matching two kinds of content:

- **Code** (`analysis/`): GPL-3.0-only, see `LICENSE`. Matches epymorph itself
  (NAU-CCL/Epymorph, GPL-3.0), which the analysis depends on.
- **Manuscript text and figures** (`manuscript/`, `results/demos/figures/`): CC BY 4.0, see
  `LICENSE-MANUSCRIPT.md`.

## Citation

See `CITATION.cff`.
