# results/demos

Everything the two case studies produce. Generated: safe to delete, rebuilt by
`just build`: minutes with `runs/` on disk, about five hours without it.

| | what | in git? |
|---|---|---|
| `figures/` | the manuscript's figures, laid out by each notebook's section 9, as PDF and PNG | yes |
| `tables/` | the score tables, as `.csv` to read and `.tex` to `\input` | yes |
| `runs/` | the runs: one folder per model, under `<demo>/seed<N>/` | **no** |
| `runs.sha256` | checksums of `runs/` | yes |
| `demo-flu.ipynb`, `demo-covid.ipynb` | the executed notebooks `just build` writes, outputs and all | **no**, for now |

A run is one model at one seed: `forecasts/<reference_date>.csv` (the quantiles of each
week's four-week forecast), `fit.csv` (the filter's fit before and after each week's
update), `params.csv` (the estimated parameters) and `run.json` (its settings). There are
twelve: three models per case study, at seeds 0 and 1.

The figures the notebooks only show (the data, the walkthrough) are deliberately not
saved: a figure in the paper must be one the build produces, and a second copy of a
figure is a second thing to drift. See `analysis/manuscript_analysis/ADDING-FIGURES.md`.

## Why `runs/` is not in git

It is 1.02 GB across 330 files, and the largest single file is a 114 MB `params.csv`,
over GitHub's 100 MB hard limit. Two ways to get it:

1. **Regenerate.** `just build` fits whatever runs are missing, four at a time: about five
   hours on one machine for all twelve. A run already on disk with the same settings is
   reused, so an interrupted build resumes.
2. **Fetch the archive.** Deposited when the repository is archived; the deposit is
   referenced from the top-level `README.md` once it exists.

Everything needed to *check the paper* is in git without either: the figures in
`figures/`, the numbers in `tables/`, and the frozen observations in `data/demos/`. The
runs are what those were computed from.

## What `runs.sha256` means

`just check` compares `runs/` against `runs.sha256`, the runs the manuscript used. `just
build` writes `runs.sha256` only when there is none, and otherwise only reports whether the
runs match, so a run that came out differently never quietly becomes the reference; after
a deliberate change, delete it and build.

A fixed seed reproduces a run **byte for byte on the same platform**, whether it runs
alone or in a parallel worker. Verified in October 2026 on the machine that made the runs:
the full season of COVID's `state` and flu's `single-strata` model at seed 0, and the
first three forecast dates of all six models, each file identical.

Across platforms, expect this check to fail and the science not to: floating-point
simulations rarely reproduce bit-exactly on different hardware or BLAS. There, compare
`tables/`, which is what the paper's claims actually rest on.

`run.json` is excluded from `runs.sha256` because it records elapsed time, which differs
every run. Everything carrying a number the analysis reads is covered.
