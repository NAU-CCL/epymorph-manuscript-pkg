# Demo 2: does spatial structure and movement buy forecast skill?

Three COVID models of the same three states, identical in every respect but one, fitted
and forecast over autumn 2020 and scored against each other.

| model | import path | structure |
|---|---|---|
| counties + commuting | `models.spatial_movement:movement` | 32 counties, ACS commuting flows between them |
| counties, no movement | `models.spatial_movement:county` | the same 32 counties, but no movement between them |
| no spatial structure | `models.state_aggregate:model` | 3 states, one node each |

The two county models live in one module because they differ by one argument, exactly as
Demo 1's two stratified models do. If they ever differ by more than that, the shared
module is the bug.

The middle model is the degraded one: it keeps the spatial resolution and removes the data
that drives it, which is what `multi-strata-homogeneous` does to age structure in Demo 1.
That is what makes the comparison say something about the *movement data* rather than
about resolution.

**All three are scored at the 3 states**, whatever they run on. A county model's 32-node
ensemble is summed to states inside each realization before quantiles are taken, because
quantiles do not add. `evaluation.py` can also read the county models at their own nodes,
which is the only scale with enough units for a distribution.

## Workflow

Run each model, then read the evaluation notebook.

```sh
source ../.venv/bin/activate
cd demo-covid

# Run all three at once. They write to separate folders and share nothing but the
# read-only observations file.
python run_season.py models.spatial_movement:movement &
python run_season.py models.spatial_movement:county &
python run_season.py models.state_aggregate:model &
wait
```

Each writes to `output/<model name>/`. A folder produced under the *same* configuration is
skipped; one produced under a different window, burn-in, seed or ensemble size is re-run,
and `--force` re-runs regardless. `python run_season.py --help` lists the options.

**600 realizations, not 200.** At 200 the per-state comparison flipped 4 of 6
state-quantity cells between seeds. The manuscript run is 600 at seeds 0 and 1. At 600 the
movement model takes about 86 minutes, the no-movement county model about 35, and the state
model about 9; `-n 100` is useful while iterating and should not be used for results.

The movement model is the slow one for a structural reason worth knowing: `mm.Pei()` takes
two movement steps a day, so it runs 56 ticks over a 4-week horizon where `mm.No()` runs 28.

The simulated window opens 2020-08-09 and runs 35 weeks. Eight burn-in weeks precede the
first forecast, so the 24 forecast origins run 2020-10-04 to 2021-03-14 with a 4-week
horizon. `Season.start_date` is the **simulation** start, with the burn-in inside the
window. It must be a Sunday, which `seasons.Season` enforces: the two ADRIOs label an MMWR
week at opposite ends, so a Saturday start puts the two observed quantities a week apart
and the deaths run ahead of the model all season. That bug was live in `covid-v02.ipynb`.

Then open `evaluation.ipynb`, which only reads `output/` and never fits anything.

## Layout

```
seasons.py            what is being forecast and over what window
models/
  covid_season.py     everything the models share: scope, population, commuting,
                      observations, initial conditions, priors, parameter table
  spatial_movement.py the two county models
  state_aggregate.py  the unstructured model
run_season.py         fit and forecast one model, write its outputs
evaluation.ipynb      diagnostics, scores, figures
evaluation.py         loading, scoring and every figure function
output/               the result: three R=600 runs at seed 0
  observations.csv    fetched once, frozen, shared by every run in this demo
  <model>/forecasts/<reference_date>.csv
  <model>/fit.csv  <model>/params.csv  <model>/run.json
output-seed1/         the seed-1 replicate, same model names; see `load_replicate`
old/                  superseded notebooks, method write-ups and runs; see its README
refactor-plan-v01.md  this package's structure and how each phase was verified
```

**`evaluation.ipynb` is hand-maintained.** It has no generator in `scratch/`: edit it
directly. Its loading, scoring and figure code lives in `evaluation.py` so the notebook and
the manuscript exporter cannot disagree, which means a new figure is a function there plus
a one-line cell here.

Shared library code lives in `../demolib/`: `forecasting.py` (the rolling-origin loop, the
scoring groups and the output writers), `ipms/covid_seirhd.py`, `scoring.py`, `plots/`.
`plots/plot_rolling_forecasts` and `plots/plot_ratio_swarm` are shared with Demo 1, so the
two demos' equivalent panels cannot drift apart.

## Data

`output/observations.csv` holds two weekly quantities per county, fetched once and frozen:

- **hospital census**, from `COVIDFacilityHospitalization` (healthdata.gov `anag-cw7u`),
  a *stock*, read as a weekly mean;
- **deaths**, from `CountyDeaths` (`ite7-j2w7`), a *flow*, read as a weekly sum.

They are fitted jointly under one likelihood, which is the epymorph capability this demo
exists to show. Neither is the other's aggregate, so there is no pooled score across them:
a census and a death count are not commensurate.

**Freezing matters more here than in Demo 1.** 40.9% of county-week death cells are
suppressed for disclosure control, and they are imputed by a truncated-Poisson draw from
the region's own per-capita mortality that week (9,798 imputed deaths across the season).
The draw uses a fixed seed, so a refetch is deterministic, but re-deriving it would still
change the target every model is scored against. It is refetched automatically when the
season window changes.

Unlike Demo 1, the underlying data are **not** revised: `ite7-j2w7` last changed 2023-04-05
and `aemt-mg7g` 2024-11-01.

Two things worth knowing about the sources. `anag-cw7u` is served from healthdata.gov, not
data.cdc.gov where it 404s. And the census is fetched at **county** scope and summed to
states by hand, never requested at `StateScope`: that ADRIO returns an entirely masked
result at state granularity, which is written up in
`../bug-reports/epymorph-facility-hospitalization-statescope.ipynb`. Summing by hand is
better here anyway, because it guarantees the county and state models see the same records.

Suppressed deaths are imputed rather than masked because the EnKF cannot take a masked
observation at more than one quantity; see `old/covid-v03.ipynb` for the runnable
reproduction.

## Reproducibility

Environment and dependencies are pinned in `../pyproject.toml` and `../uv.lock`
(`epymorph==2.0.0b1`, Python 3.12). Each run records its own provenance in
`output/<model>/run.json`, including the structural knobs that define the comparison:
`aggregate_quantities`, `scoring_locations`, `movement_data_mode` and whether
`forecast_dynamics` was used. Section 3 of `evaluation.ipynb` asserts that the three runs
differ in none of the fields they must share.

Initial conditions are drawn per node from a stream keyed on FIPS, so dropping a state from
the roster does not change any surviving node's values, and all three models get the same
state-level values at a given seed. `models.covid_season.parameter_table()` returns every
fixed parameter with its value and units.

`CENSUS_API_KEY` must be set in `../.env` for the ACS population and commuting ADRIOs.

## Where the reasoning lives

- `old/ifr-methods.md` — the infection fatality ratio and how it was derived
- `old/covid-v03.ipynb` — where the model, the data alignment and the seeding are worked out
- `refactor-plan-v01.md` — this package's structure and how it was verified
- `../project-notes/handoff.md` — ensemble size, the window fix, the seeding defects, and
  the results of every run
