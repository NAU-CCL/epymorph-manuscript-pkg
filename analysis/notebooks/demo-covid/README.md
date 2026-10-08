# Demo 2: does spatial structure and movement buy forecast skill?

Three COVID models of the same three states (MA, CT, NH), identical in every respect but
one, fitted and forecast over autumn 2020 and scored against each other.

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

### A sensitivity analysis: correlated parameter shocks

Summed to states, the county models are overconfident at longer horizons. The candidate
mechanism is that each county's parameters wander independently, so their errors partly
cancel in the sum. Four more models test it by correlating the counties' daily parameter
shocks in space (`models/correlated_ou.py`, adapted from
`FluSight-pipeline/flu/correlated.py`), while filtering and while forecasting:

| model | import path | correlation |
|---|---|---|
| `county-correlated` | `models.spatial_movement:county_correlated` | fitted to the data (`CORRELATION_FITTED`) |
| `movement-correlated` | `models.spatial_movement:movement_correlated` | fitted to the data |
| `county-correlated-strong` | `models.spatial_movement:county_correlated_strong` | a pure kernel, an upper bracket (`CORRELATION_STRONG`) |
| `movement-correlated-strong` | `models.spatial_movement:movement_correlated_strong` | a pure kernel |

They are not part of the three-model comparison, and nothing in the manuscript's tables or
figures reads them. `03-correlated-ou.ipynb` sets out the design, how the correlation
was chosen without forecast scores, and the results.

## The notebooks

| notebook | what it does | needs |
|---|---|---|
| `01-model-and-forecast.ipynb` | builds the three models in epymorph, fits each up to two weeks before the winter peak, and issues one four-week forecast; then checks that its models are identical to the ones below | a Census API key; about 30 minutes |
| `02-evaluation.ipynb` | every table and figure the manuscript reports for Demo 2 | the ensembles |
| `03-correlated-ou.ipynb` | the correlated-OU sensitivity analysis | its own ensembles |

Start with `01`: it is the whole workflow, once, with every epymorph call in view. `02` is
that workflow repeated at 24 forecast dates and scored, which is what the rest of this
README is about.

## Workflow

Run each model, then read `02-evaluation.ipynb`. From `analysis/`:

```sh
# Run all three at once. They write to separate folders and share nothing but the
# read-only observations file.
for spec in models.spatial_movement:movement models.spatial_movement:county \
            models.state_aggregate:model; do
  uv run python -m manuscript_analysis.demos.covid.run_season $spec -n 600 --seed 0 &
done
wait
```

`../scripts/run-demos.sh` does this for both demos and both seeds.

Each writes to `results/demos/runs/covid/seed<N>/<model name>/`. A folder produced under
the *same* configuration is skipped; one produced under a different window, burn-in, seed
or ensemble size is re-run, and `--force` re-runs regardless. `--help` lists the options.

**Always pass `-n 600`.** The command line's default is Demo 1's 300. At 200 the
per-state comparison flipped 4 of 6 state-quantity cells between seeds; the manuscript run
is 600 at seeds 0 and 1. At 600 the movement model takes about 86 minutes, the no-movement
county model about 35, and the state model about 9. `-n 100` is useful while iterating and
should not be used for results; below that the filter can fail outright.

The movement model is the slow one for a structural reason worth knowing: `mm.Pei()` takes
two movement steps a day, so it runs 56 ticks over a 4-week horizon where `mm.No()` runs 28.

The simulated window opens 2020-08-09 and runs 35 weeks. Eight burn-in weeks precede the
first forecast, so the 24 forecast origins run 2020-10-04 to 2021-03-14 with a 4-week
horizon. `Season.start_date` is the **simulation** start, with the burn-in inside the
window. It must be a Sunday, which `seasons.Season` enforces: the two ADRIOs label an MMWR
week at opposite ends, so a Saturday start puts the two observed quantities a week apart
and the deaths run ahead of the model all season.

The sensitivity runs go to `results/demos/notebook/correlated-ou/covid/seed<N>/` instead,
by passing `-o`; `03-correlated-ou.ipynb` has the commands. That tree is gitignored and
outside `MANIFEST.sha256`, so the manuscript's ensembles are untouched by it.

`02-evaluation.ipynb` and `03-correlated-ou.ipynb` only read run outputs and never fit
anything.

## Layout

```
analysis/src/manuscript_analysis/demos/covid/
  seasons.py            what is being forecast and over what window
  models/
    covid_season.py     everything the models share: scope, population, commuting,
                        observations, initial conditions, priors, parameter table,
                        and the two correlation settings
    spatial_movement.py the county models, with and without correlated shocks
    state_aggregate.py  the unstructured model
    correlated_ou.py    the spatially correlated Ornstein-Uhlenbeck process
  run_season.py         fit and forecast one model, write its outputs
  evaluation.py         loading, scoring and every figure function
analysis/notebooks/demo-covid/
  01-model-and-forecast.ipynb  the models, one fit, one forecast
  02-evaluation.ipynb   the manuscript's tables and figures
  03-correlated-ou.ipynb       the sensitivity analysis

data/demos/covid/observations.csv           fetched once, frozen, shared by every run
results/demos/runs/covid/seed0/<model>/     the manuscript run; seed1/ is the replicate
  forecasts/<reference_date>.csv  fit.csv  params.csv  run.json
results/demos/notebook/correlated-ou/covid/ the sensitivity runs, same layout
```

**The notebooks are hand-maintained**: edit them directly. `01` writes the models out in
full, so its last cell checks them against `models/` and fails if the two copies have
drifted apart. `02`'s loading, scoring and figure code lives in `evaluation.py` so the
notebook and the manuscript exporter cannot disagree, which means a new figure is a
function there plus a one-line cell here.

Shared library code lives in `analysis/src/manuscript_analysis/demos/lib/`:
`forecasting.py` (the rolling-origin loop, the scoring groups and the output writers),
`ipms/covid_seirhd.py`, `scoring.py`, `plots/`. `plots.plot_rolling_forecasts` and
`plots.plot_ratio_swarm` are shared with Demo 1, so the two demos' equivalent panels
cannot drift apart.

## Data

`data/demos/covid/observations.csv` holds two weekly quantities per county, fetched once
and frozen:

- **hospital census**, from `COVIDFacilityHospitalization` (healthdata.gov `anag-cw7u`),
  a *stock*, read as a weekly mean;
- **deaths**, from `CountyDeaths` (`ite7-j2w7`), a *flow*, read as a weekly sum.

They are fitted jointly under one likelihood, which is the epymorph capability this demo
exists to show. Neither is the other's aggregate, so there is no pooled score across them:
a census and a death count are not commensurate.

**Freezing matters more here than in Demo 1.** 41.2% of county-week death cells are
suppressed for disclosure control, and they are imputed by a truncated-Poisson draw from
the region's own per-capita mortality that week (1,762 imputed deaths across the season).
The draw uses a fixed seed, so a refetch is deterministic, but re-deriving it would still
change the target every model is scored against. It is never refetched automatically: if
the file is missing or does not cover the season window, loading stops with an error, and
`covid_season.fetch_observations()` is the deliberate way to replace it.

Unlike Demo 1, the underlying data are **not** revised: `ite7-j2w7` last changed 2023-04-05
and `aemt-mg7g` 2024-11-01.

Two things worth knowing about the sources. `anag-cw7u` is served from healthdata.gov, not
data.cdc.gov where it 404s. And the census is fetched at **county** scope and summed to
states by hand, never requested at `StateScope`: that ADRIO returns an entirely masked
result at state granularity. Summing by hand is better here anyway, because it guarantees
the county and state models see the same records.

Suppressed deaths are imputed rather than masked because the EnKF cannot take a masked
observation at more than one quantity.

## Reproducibility

Environment and dependencies are pinned in `analysis/pyproject.toml` and
`analysis/uv.lock` (`epymorph==2.0.0b1`, Python 3.12). Each run records its own provenance
in `run.json`, including the structural knobs that define the comparison:
`aggregate_quantities`, `scoring_locations`, `movement_data_mode` and whether
`forecast_dynamics` was used. `02-evaluation.ipynb` asserts that the three runs differ in
none of the fields they must share.

Initial conditions are drawn per node from a stream keyed on FIPS, so dropping a state from
the roster does not change any surviving node's values, and all three models get the same
state-level values at a given seed. `models.covid_season.parameter_table()` returns every
fixed parameter with its value and units.

The ACS population and commuting inputs are frozen in `data/raw/` with their provenance,
so the runs and the evaluation need no Census API key. The exception is
`01-model-and-forecast.ipynb`, which fetches them live to show the ADRIOs at work. The county internal points the correlated
models use come from TIGER, which needs no key.

## Where the reasoning lives

These are in the maintainer's working folder, not in this repository:

- `demo-covid/old/ifr-methods.md`: the infection fatality ratio and how it was derived
- `demo-covid/old/covid-v03.ipynb`: where the model, the data alignment and the seeding
  were worked out, including the runnable reproduction of the masked-observation limit
- `demo-covid/refactor-plan-v01.md`: the package's structure and how it was verified
- `project-notes/handoff.md`: ensemble size, the window fix, the seeding defects, and
  the results of every run
- `bug-reports/epymorph-facility-hospitalization-statescope.ipynb`: the masked
  `StateScope` result
