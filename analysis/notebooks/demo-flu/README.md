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

Run each model, then read the evaluation notebook.

```sh
source ../.venv/bin/activate
cd demo-flu

# Run all three at once. Each fit is single-threaded and uses about 0.5 GB, so on any
# multi-core machine this costs the same wall-clock as the slowest model rather than
# the sum of all three. They write to separate folders and share nothing but the
# read-only observations file.
python run_season.py models.multi_strata_flu:empirical &
python run_season.py models.multi_strata_flu:homogeneous &
python run_season.py models.single_strata &
wait
```

Sequentially, if you would rather watch one at a time:

```sh
python run_season.py models.multi_strata_flu:empirical
python run_season.py models.multi_strata_flu:homogeneous
python run_season.py models.single_strata
```

Each writes to `output/<model name>/`. A folder produced under the *same* configuration is
skipped; one produced under a different season window, burn-in or seed is re-run, and
`--force` re-runs regardless. `python run_season.py --help` lists the options; the defaults
reproduce the manuscript run (300 realizations, seed 0, and the season's own 10-week burn-in
and 4-week horizon).

**300 realizations, not 100.** At 100 the per-jurisdiction comparison was not reproducible
across seeds; at 300 it largely is. A stratified model takes about 5 hours at 300 and about
80 minutes at 100, so `-n 100` is useful while iterating and should not be used for results.

The season spans the full FluSight 2025-26 challenge: the simulated window opens 2025-09-13,
ten burn-in weeks precede the first forecast, and the 25 forecast origins run 2025-11-22 to
2026-05-30. Note `Season.start_date` is the **simulation** start, with the burn-in inside the
window; a FluSight challenge's dates are its *forecast* window instead.

Budget about an hour per stratified model and five minutes for the unstratified one.

Then open `evaluation.ipynb`, which only reads `output/` and never fits anything.

## Layout

```
seasons.py            what is being forecast and over what window
models/
  flu_season.py       everything the models share: scope, demography, severity,
                      observations, initial conditions, priors, parameter table
  multi_strata_flu.py the two stratified models
  single_strata.py    the unstratified model
run_season.py         fit and forecast one model, write its outputs
evaluation.ipynb      diagnostics, scores, figures
output/               the result: three R=300 runs at seed 0
  observations.csv    fetched once, frozen, shared by every run in this demo
  <model>/forecasts/<reference_date>.csv
  <model>/fit.csv  <model>/params.csv  <model>/run.json
output-r100/          the superseded 100-realization runs; see its README
sensitivity/          seed-1 replicates and the severity sweep; see its README
superseded/           the retired notebook pipeline; see its README
```

Everything else at this level is documentation: `contact-matrix-methods.md`,
`ihr-revision.md`, `refactor-plan-v01.md`, `demo-plan-v02.md`. Two notebooks stay here and
are neither superseded nor part of the comparison: `state-contact-sources.ipynb`, the
robustness check `contact-matrix-methods.md` section 9.0 cites by name, and
`multi-strata-tutorial.ipynb`, which builds one unfitted model start to finish as teaching
material.

`evaluation.ipynb` reads `output/` only, and `figure_relative_wis_swarm` additionally reads
`sensitivity/` through `evaluation.load_replicate()` for its second seed. The other
directories exist so the ensemble-size and severity findings stay reproducible.

**`evaluation.ipynb` is hand-maintained.** It has no generator in `scratch/`, unlike every
other notebook in this project: edit it directly. Its loading, scoring and figure code lives
in `evaluation.py` so that the notebook and the manuscript exporter cannot disagree, which
means a new figure is a function there plus a one-line cell here.

Shared library code lives in `../demolib/`: `forecasting.py` (the rolling-origin loop
and the output writers), `ipms/flu_age_mixing.py` (the multi-strata builder),
`scoring.py`, `contacts.py`, `plots/`.

## Data

`output/observations.csv` holds weekly influenza admissions from CDC's
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

Environment and dependencies are pinned in `../pyproject.toml` and `../uv.lock`
(`epymorph==2.0.0b1`, Python 3.12). Each run records its own provenance in
`output/<model>/run.json`: season, realizations, window, seed, elapsed time, and the
observations file it used. `models.flu_season.parameter_table()` returns every fixed
parameter with its value and units.

`CENSUS_API_KEY` must be set in `../.env` for the ACS demography ADRIOs.

## Where the reasoning lives

Code here is kept terse on purpose. The reasoning behind the design sits in:

- `contact-matrix-methods.md` — contact structure, projection, mixing variants
- `ihr-revision.md` — severity, and why the foundational demo's values were rebuilt
- `refactor-plan-v01.md` — this package's structure and how it was verified
- `../project-notes/handoff.md` — ensemble size, eta damping, the seeding floor,
  and the results of every run
