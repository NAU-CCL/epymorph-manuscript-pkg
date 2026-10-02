# Demo 1: does age structure buy forecast skill?

Three influenza models, identical in every respect but one, fitted and forecast over the
2025-26 season and scored against each other.

| model | import path | structure |
|---|---|---|
| multi-strata, empirical mixing | `models.multi_strata_flu:empirical` | six age strata, the Mistry et al. contact matrix projected onto this demography |
| multi-strata, homogeneous mixing | `models.multi_strata_flu:homogeneous` | six age strata, but contact in proportion to group size |
| single-strata | `models.single_strata` | one population, no age structure |

The two multi-strata models live in one module because they differ by one argument. If
they ever differ by more than that, the shared module is the bug.

## Workflow

Run each model, then read `evaluation.ipynb`. From `analysis/`:

```sh
# Run all three at once. Each fit is single-threaded and uses about 0.5 GB, so on any
# multi-core machine this costs the same wall-clock as the slowest model rather than
# the sum of all three. They write to separate folders and share nothing but the
# read-only observations file.
for spec in models.multi_strata_flu:empirical models.multi_strata_flu:homogeneous \
            models.single_strata; do
  uv run python -m manuscript_analysis.demos.flu.run_season $spec --seed 0 &
done
wait
```

`../scripts/run-demos.sh` does this for both demos and both seeds.

Each writes to `results/demos/runs/flu/seed<N>/<model name>/`. A folder produced under the
*same* configuration is skipped; one produced under a different season window, burn-in,
seed or ensemble size is re-run, and `--force` re-runs regardless. `--help` lists the
options; the defaults reproduce the manuscript run (300 realizations, seed 0, and the
season's own 10-week burn-in and 4-week horizon).

**300 realizations, not 100.** At 100 the per-jurisdiction comparison was not reproducible
across seeds; at 300 it largely is. At 300 a stratified model takes about 3 to 4 hours
(empirical mixing about 4, homogeneous about 3.2) and the single-strata model about 25
minutes, so `-n 100` is useful while iterating and should not be used for results.

The season spans the full FluSight 2025-26 challenge: the simulated window opens 2025-09-13
and runs 38 weeks, ten burn-in weeks precede the first forecast, and the 25 forecast dates
run 2025-11-22 to 2026-05-09, so the last four-week forecast reaches 2026-05-30. Note `Season.start_date` is the **simulation** start, with the
burn-in inside the window; a FluSight challenge's dates are its *forecast* window instead.

`evaluation.ipynb` only reads run outputs and never fits anything.

## Layout

```
analysis/src/manuscript_analysis/demos/flu/
  seasons.py            what is being forecast and over what window
  models/
    flu_season.py       everything the models share: scope, demography, severity,
                        observations, initial conditions, priors, parameter table
    multi_strata_flu.py the two stratified models
    single_strata.py    the unstratified model
  run_season.py         fit and forecast one model, write its outputs
  evaluation.py         loading, scoring and every figure function
analysis/notebooks/demo-flu/
  evaluation.ipynb      diagnostics, scores, figures

data/demos/flu/observations.csv           fetched once, frozen, shared by every run
results/demos/runs/flu/seed0/<model>/     the manuscript run; seed1/ is the replicate
  forecasts/<reference_date>.csv  fit.csv  params.csv  run.json
```

`evaluation.ipynb` reads seed 0, and `figure_relative_wis_swarm` additionally reads seed 1
through `evaluation.load_replicate()`.

**`evaluation.ipynb` is hand-maintained**: edit it directly. Its loading, scoring and
figure code lives in `evaluation.py` so that the notebook and the manuscript exporter
cannot disagree, which means a new figure is a function there plus a one-line cell here.

Shared library code lives in `analysis/src/manuscript_analysis/demos/lib/`:
`forecasting.py` (the rolling-origin loop and the output writers), `ipms/flu_age_mixing.py`
(the multi-strata builder), `scoring.py`, `contacts.py`, `plots/`.

## Data

`data/demos/flu/observations.csv` holds weekly influenza admissions from CDC's
`CurrentStateAdmissions`, one row per date, location and stratum. It is fetched once and
every model is fitted and scored against it, so all three share an identical target.

**This file is deliberately frozen.** The ADRIO reads CDC's `mpgq-jmmr`, whose title ends in
"(Preliminary)" and which CDC updates every Wednesday, so the counts move: a re-run two weeks
after the first gave a materially different result from the same code. It is refetched
automatically when the season window changes, and deleting it forces a refetch. Expect the
numbers to move if you do.

A finalized sibling dataset, `ua7e-t2fy`, has identical columns and coverage and currently
differs from the preliminary one by 15 admissions across the whole season, but no epymorph
ADRIO reads it. The plan is to stay on the built-in ADRIO and re-run before submission.

Two details worth knowing. The six age bands do not quite sum to CDC's own all-ages
total (about 0.25% short); the reported total is stored as a `total_reported` row for
checking, but every model is fitted on the sum of bands. And Puerto Rico is forecast,
as FluSight requires, but excluded from the model comparison, because its influenza
seasonality is tropical rather than temperate and these models assume a single winter
peak (`seasons.UNSCORED_STATES`).

## Reproducibility

Environment and dependencies are pinned in `analysis/pyproject.toml` and
`analysis/uv.lock` (`epymorph==2.0.0b1`, Python 3.12). Each run records its own provenance
in `run.json`: season, realizations, window, seed, elapsed time, and the observations file
it used. `models.flu_season.parameter_table()` returns every fixed parameter with its value
and units.

`CENSUS_API_KEY` must be set in the repository-root `.env` for the ACS demography ADRIOs.

## Where the reasoning lives

Code here is kept terse on purpose. The reasoning behind the design is in the maintainer's
working folder, not in this repository:

- `demo-flu/contact-matrix-methods.md`: contact structure, projection, mixing variants
- `demo-flu/ihr-revision.md`: severity, and why the foundational demo's values were rebuilt
- `demo-flu/refactor-plan-v01.md`: the package's structure and how it was verified
- `demo-flu/demo-plan-v02.md`: the demo's design
- `demo-flu/state-contact-sources.ipynb`: the robustness check
  `contact-matrix-methods.md` section 9.0 cites by name
- `demo-flu/multi-strata-tutorial.ipynb`: one unfitted model built start to finish, as
  teaching material
- `demo-flu/output-r100/`, `demo-flu/sensitivity/`: the superseded 100-realization runs,
  the original seed-1 replicates and the severity sweep
- `project-notes/handoff.md`: ensemble size, eta damping, the seeding floor, and the
  results of every run
