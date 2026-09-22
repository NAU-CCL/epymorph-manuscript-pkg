# epymorph-manuscript-pkg

Reproducibility package for the epymorph manuscript: data, analysis code and manuscript
source in one repository with one git history, following FAIR4RS principles.

The goal it is built to: **nothing in the manuscript asserts a number the code cannot
reproduce.** Every figure, table and quoted count is generated, and `scripts/check.sh`
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
cd analysis && uv sync
cp .env.example .env          # then add a free Census API key
```

The key is needed for the demography and commuting data the models pull from the Census
API. It is **not** needed for the CDC surveillance series: those are revised weekly, so
they are frozen in `data/demos/` rather than re-fetched.

### 2. Get the ensembles

Either regenerate them, which is the slow half of the analysis:

```bash
scripts/run-demos.sh          # ~8-10 h, three single-threaded fits at a time
```

or fetch the archived outputs (see `results/demos/README.md`). A run folder produced
under the same configuration is skipped, so an interrupted run resumes rather than
starting over.

### 3. Build everything the manuscript uses

```bash
scripts/build-figures.sh      # seconds
```

Writes `results/figures/` (five composed figures) and `results/demos/tables/` (six
tables, each as a `.csv` to read and a `.tex` to `\input`).

### 4. Check it

```bash
scripts/check.sh
```

Three self-contained checks, each regenerating something and comparing it against what is
committed: the literature-search pipeline's own eight assertions, the demo tables against
a fresh generation, and the ensembles against `MANIFEST.sha256`. The demo checks are
skipped, with a message, when the ensembles are absent.

### 5. Explore, if you want to

```bash
cd analysis && uv run jupyter lab notebooks/
```

`notebooks/demo-flu/evaluation.ipynb` and `notebooks/demo-covid/evaluation.ipynb` run the
models, score them, draw every panel individually, and render the composed manuscript
figures. They are the readable surface; `scripts/build-figures.sh` is the same work
without the commentary.

---

## What is here

```
data/
  demos/{flu,covid}/observations.csv   frozen surveillance. Cannot be re-derived.
  lit-search/raw/                      archived search exports
  lit-search/decisions/                hand-entered screening calls
analysis/
  pyproject.toml                       one uv environment
  src/manuscript_analysis/
    demos/          the two vignettes: lib/, flu/, covid/, export.py, tables.py
    lit_search/     the software-landscape search pipeline
  notebooks/        the driver notebooks
manuscript/         LaTeX, one file per section; round-trips with Overleaf
results/
  figures/          the manuscript's figures
  demos/tables/     the manuscript's tables, .csv and .tex
  demos/runs/       the ensembles. NOT in git.
  lit-search/       shortlists, register, PRISMA flow, Table 1
scripts/            run-demos.sh, build-figures.sh, check.sh, sync-manuscript.sh
```

Each subdirectory has its own README with the detail.

### The two analyses

**The software landscape** (`lit_search`) surveys comparable packages. It arrived
2026-09-21 and was the first piece here that ran end to end; it is the working model for
everything else. `python -m manuscript_analysis.lit_search --check` regenerates
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

Generated tables and figures travel the other way: `results/` is built here, and the
manuscript `\input`s or includes them. **Never hand-edit a generated table**, in either
repository; `scripts/check.sh` is what catches it if someone does.

---

## Still to come

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
- **Manuscript text and figures** (`manuscript/`, `results/figures/`): CC BY 4.0, see
  `LICENSE-MANUSCRIPT.md`.

## Citation

See `CITATION.cff`.
