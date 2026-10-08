# results/demos

Everything the two demonstration vignettes produce. Generated: safe to delete, rebuilt by
`scripts/build-figures.sh` (about 2 minutes) on top of `scripts/run-demos.sh` (hours).

| | what | in git? |
|---|---|---|
| `figures/` | the manuscript's figures, composed by the exporter | yes |
| `runs/` | the ensembles: one folder per model, under `<demo>/seed<N>/` | **no** |
| `tables/` | the score tables, as `.csv` to read and `.tex` to `\input` | yes |
| `notebook/` | whatever the notebooks save while you run them, and the executed copy of `demo-covid.ipynb` that `scripts/run-demos.sh` writes | **no** — exploratory |
| `MANIFEST.sha256` | checksums of `runs/` | yes |

The notebooks' per-panel figures are deliberately not carried: they are the exploratory
view of panels the exporter composes properly into `figures/`, and a second copy
of a figure is a second thing to drift.

## Why `runs/` is not in git

It is 1.02 GB across 318 files, and the largest single file is a 114 MB `params.csv` --
over GitHub's 100 MB hard limit. Two ways to get it:

1. **Regenerate.** `scripts/run-demos.sh`, roughly 8-10 hours wall clock on one machine,
   three single-threaded fits at a time. A run folder produced under the same
   configuration is skipped, so an interrupted run resumes.
2. **Fetch the archive.** Deposited when the repository is archived; the deposit is
   referenced from the top-level `README.md` once it exists.

Everything needed to *check the paper* is in git without either: the figures in
`figures/`, the numbers in `tables/`, and the frozen observations in
`data/demos/`. The ensembles are what those were computed from.

## What the manifest means

`python -m manuscript_analysis.demos.manifest --check` compares `runs/` against the
ensembles the manuscript used. A fixed seed reproduces a run **byte for byte on the same
platform** -- verified 2026-09-22 by re-running COVID's `state` model at seed 0 and
getting identical `fit.csv`, `params.csv` and all 24 forecast files.

Across platforms, expect this check to fail and the science not to: floating-point
ensembles rarely reproduce bit-exactly on different hardware or BLAS. There, compare
`tables/`, which is what the paper's claims actually rest on.

`run.json` is excluded from the manifest because it records elapsed time, which differs
every run. Everything carrying a number the analysis reads is covered.
