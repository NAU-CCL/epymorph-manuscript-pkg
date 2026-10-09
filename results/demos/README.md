# results/demos

Everything the two demonstration vignettes produce. Generated: safe to delete, rebuilt by
`just build`: minutes with `runs/` on disk, about five hours without it.

| | what | in git? |
|---|---|---|
| `figures/` | the manuscript's figures, composed by the exporter | yes |
| `runs/` | the ensembles: one folder per model, under `<demo>/seed<N>/` | **no** |
| `tables/` | the score tables, as `.csv` to read and `.tex` to `\input` | yes |
| `demo-flu.ipynb`, `demo-covid.ipynb` | the executed notebooks `just build` writes, outputs and all | **no**, for now |
| `runs.sha256` | checksums of `runs/` | yes |

The notebooks' per-panel figures are deliberately not carried: they are the exploratory
view of panels the exporter composes properly into `figures/`, and a second copy
of a figure is a second thing to drift.

## Why `runs/` is not in git

It is 1.02 GB across 318 files, and the largest single file is a 114 MB `params.csv` --
over GitHub's 100 MB hard limit. Two ways to get it:

1. **Regenerate.** `just build` fits whatever runs are missing, four at a time: about five
   hours on one machine for all twelve. A run already on disk with the same settings is
   reused, so an interrupted build resumes.
2. **Fetch the archive.** Deposited when the repository is archived; the deposit is
   referenced from the top-level `README.md` once it exists.

Everything needed to *check the paper* is in git without either: the figures in
`figures/`, the numbers in `tables/`, and the frozen observations in
`data/demos/`. The ensembles are what those were computed from.

## What the manifest means

`just check` compares `runs/` against `runs.sha256`, the runs the manuscript used. `just
build` writes `runs.sha256` only when there is none, so a run that came out differently
never quietly becomes the reference; after a deliberate change, delete it and build. A fixed seed reproduces a run **byte for byte on the same
platform** -- verified 2026-09-22 by re-running COVID's `state` model at seed 0 and
getting identical `fit.csv`, `params.csv` and all 24 forecast files.

Across platforms, expect this check to fail and the science not to: floating-point
ensembles rarely reproduce bit-exactly on different hardware or BLAS. There, compare
`tables/`, which is what the paper's claims actually rest on.

`run.json` is excluded from `runs.sha256` because it records elapsed time, which differs
every run. Everything carrying a number the analysis reads is covered.
