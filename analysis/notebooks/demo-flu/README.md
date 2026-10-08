# Demo 1: does age structure buy forecast skill?

Three influenza models, identical in every respect but one, fitted and forecast over the
2025-26 season and scored against each other.

| model | structure |
|---|---|
| `multi-strata-empirical` (empirical mixing) | six age groups, the Mistry et al. contact matrix projected onto each state's age distribution |
| `multi-strata-homogeneous` (homogeneous mixing) | six age groups, but contact in proportion to group size |
| `single-strata` (no age structure) | one population |

## Where it is

**`analysis/src/manuscript_analysis/demo-flu.ipynb`** is the whole analysis, read top to
bottom: the data, the age-mixing model, one fit and forecast of the `single-strata` model
explained, the two stratified models as one change each, the rolling forecasts of all
three at both seeds, and the scores, figures and tables the manuscript reports for Demo 1.
It is run by papermill (`scripts/run-demos.sh`, `scripts/build-figures.sh`) and can be
opened in Jupyter where it lives. A run already on disk with the same settings is reused;
a missing one is fitted, four at a time. At 300 realizations a stratified model takes
about 3 to 4 hours and the single-strata model about 25 minutes.

| file | what |
|---|---|
| `manuscript_analysis/demo-flu.ipynb` | the models, the walkthrough, the runs, the scores, figures and tables |
| `manuscript_analysis/flu_inputs.py` | data preparation that is not epymorph: the frozen observations, severity, the contact matrices, initial conditions |
| `manuscript_analysis/runs.py`, `scoring.py`, `plots.py`, `util.py` | writing and reading runs, scoring, drawing a panel, writing a table; shared with Demo 2 |
| `data/demos/flu/observations.csv` | the CDC observations, fetched once and frozen |
| `data/raw/flu-population-*.npz`, `data/raw/mistry/` | the ACS age structure and the Mistry contact matrix, frozen with their provenance |
| `results/demos/runs/flu/seed<N>/<model>/` | the runs: `forecasts/<reference_date>.csv`, `fit.csv`, `params.csv`, `run.json` |
| `scripts/fetch_flu_observations.py` | how the observations were fetched; no build runs it |

The season spans the full FluSight 2025-26 challenge: the simulated window opens 2025-09-13
and runs 38 weeks, ten burn-in weeks precede the first forecast, and the 25 forecast dates
run 2025-11-22 to 2026-05-09, so the last four-week forecast reaches 2026-05-30.

**300 realizations, not 100.** At 100 the per-jurisdiction comparison was not reproducible
across seeds; at 300 it largely is.

## Data

`data/demos/flu/observations.csv` holds weekly influenza admissions from CDC's
`CurrentStateAdmissions`, one row per date, location and stratum. It is fetched once and
every model is fitted and scored against it, so all three share an identical target.

**This file is deliberately frozen.** The ADRIO reads CDC's `mpgq-jmmr`, whose title ends in
"(Preliminary)" and which CDC updates every Wednesday, so the counts move: a re-run two weeks
after the first gave a materially different result from the same code. It is never
refetched automatically: if the file is missing or does not cover the season window,
loading stops with an error. `scripts/fetch_flu_observations.py` records how it was made,
and writes a fresh copy to compare; expect the numbers to move.

A finalized sibling dataset, `ua7e-t2fy`, has identical columns and coverage and currently
differs from the preliminary one by 15 admissions across the whole season, but no epymorph
ADRIO reads it. The plan is to stay on the built-in ADRIO and re-run before submission.

Two details worth knowing. The six age bands do not quite sum to CDC's own all-ages
total (about 0.25% short); the reported total is stored as a `total_reported` row for
checking, but every model is fitted on the sum of bands. And Puerto Rico is forecast,
as FluSight requires, but excluded from the model comparison, because its influenza
seasonality is tropical rather than temperate and these models assume a single winter
peak (`UNSCORED` in the notebook).

## Reproducibility

Environment and dependencies are pinned in `analysis/pyproject.toml` and
`analysis/uv.lock` (`epymorph==2.0.0b1`, Python 3.12). Each run records its settings in
`run.json`. A fixed seed reproduces a run byte for byte on the same platform, whether it
runs alone or in a parallel worker.

The ACS age structure (the table and each group's sum) and the Mistry contact matrix are
frozen in `data/raw/` with their provenance, so nothing here needs a Census API key.

## Where the reasoning lives

Code here is kept terse on purpose. The reasoning behind the design is in the maintainer's
working folder, not in this repository:

- `demo-flu/contact-matrix-methods.md`: contact structure, projection, mixing variants
- `demo-flu/ihr-revision.md`: severity, and why the foundational demo's values were rebuilt
- `demo-flu/refactor-plan-v01.md`: the package's structure before the restructure
- `demo-flu/demo-plan-v02.md`: the demo's design
- `demo-flu/state-contact-sources.ipynb`: the robustness check
  `contact-matrix-methods.md` section 9.0 cites by name
- `demo-flu/multi-strata-tutorial.ipynb`: one unfitted model built start to finish, as
  teaching material
- `demo-flu/output-r100/`, `demo-flu/sensitivity/`: the superseded 100-realization runs,
  the original seed-1 replicates and the severity sweep
- `project-notes/handoff.md`: ensemble size, eta damping, the seeding floor, and the
  results of every run
