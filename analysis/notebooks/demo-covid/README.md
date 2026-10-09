# Demo 2: does spatial structure and movement buy forecast skill?

Three COVID models of the same three states (MA, CT, NH), identical in every respect but
one, fitted and forecast over autumn 2020 and scored against each other.

| model | structure |
|---|---|
| `movement` (counties + commuting) | 32 counties, ACS commuting flows between them |
| `county` (counties, no movement) | the same 32 counties, but no movement between them |
| `state` (no spatial structure) | 3 states, one node each |

The middle model is the degraded one: it keeps the spatial resolution and removes the data
that drives it, which is what `multi-strata-homogeneous` does to age structure in Demo 1.
That is what makes the comparison say something about the *movement data* rather than
about resolution.

**All three are scored at the 3 states**, whatever they run on. A county model's 32-node
ensemble is summed to states inside each realization before quantiles are taken, because
quantiles do not add. Its forecasts are also written at its own counties, which is the
only scale with enough units for a distribution.

## Where it is

**`analysis/manuscript_analysis/demo-covid.ipynb`** is the whole analysis, read top to
bottom: the data, the SEIRHD model, one fit and forecast of the `state` model explained,
the other two models as one change each, and the rolling forecasts of all three at both
seeds. It is run by papermill (`just build`) and can be opened in Jupyter
where it lives. A run already on disk with the same settings is reused; a missing one is
fitted, four at a time. At 600 realizations the movement model takes about 86 minutes,
`county` about 35 and `state` about 9.

It then scores the runs and makes every Demo 2 figure and table the manuscript uses:
Figure 3, the supplement's rolling forecasts and calibration panel (b), and its three
tables. With `output_dir` set (a build sets it) they are written to `results/demos/`.

| file | what |
|---|---|
| `manuscript_analysis/demo-covid.ipynb` | the models, the walkthrough, the runs, the scores, figures and tables |
| `manuscript_analysis/covid_inputs.py` | data preparation that is not epymorph: the frozen observations, initial conditions |
| `manuscript_analysis/runs.py` | writing a run to disk, whether one is there, reading it back |
| `manuscript_analysis/scoring.py`, `plots.py`, `util.py` | scoring, drawing a panel, writing a table; shared with Demo 1 |
| `data/demos/covid/observations.csv` | the CDC observations, fetched once and frozen |
| `data/raw/covid-*.npz` | the ACS population and commuting, frozen with their provenance |
| `results/demos/runs/covid/seed<N>/<model>/` | the runs: `forecasts/<reference_date>.csv`, `fit.csv`, `params.csv`, `run.json` |
| `scripts/fetch_covid_observations.py` | how the observations were fetched and imputed; no build runs it |

The simulated window opens Sunday 2020-08-09 and runs 35 weeks. Eight burn-in weeks precede
the first forecast, so the 24 forecast dates run 2020-10-04 to 2021-03-14 with a 4-week
horizon. The start must be a Sunday: the two CDC series label an MMWR week at opposite
ends, so a Saturday start puts the two observed quantities a week apart.

## Data

`data/demos/covid/observations.csv` holds two weekly quantities per county, fetched once
and frozen:

- **hospital census**, from `COVIDFacilityHospitalization` (healthdata.gov `anag-cw7u`),
  a *stock*, read as a weekly mean;
- **deaths**, from `CountyDeaths` (`ite7-j2w7`), a *flow*, read as a weekly sum.

They are fitted jointly under one likelihood, which is the epymorph capability this demo
exists to show. Neither is the other's aggregate, so there is no pooled score across them:
a census and a death count are not commensurate.

41.2% of county-week death cells are suppressed for disclosure control. They are imputed
by a truncated-Poisson draw from the region's own per-capita mortality that week (1,762
imputed deaths across the season), with a fixed seed. The sources are no longer revised
(`ite7-j2w7` last changed 2023-04-05, `aemt-mg7g` 2024-11-01), and on 2026-10-08
`scripts/fetch_covid_observations.py` reproduced the frozen file byte for byte. It is
never refetched automatically: if the file does not cover the season, loading stops.

Two things worth knowing about the sources. `anag-cw7u` is served from healthdata.gov, not
data.cdc.gov where it 404s. And the census is fetched at **county** scope and summed to
states by hand, never requested at `StateScope`: that ADRIO returns an entirely masked
result at state granularity. Summing by hand is better here anyway, because it guarantees
the county and state models see the same records.

Suppressed deaths are imputed rather than masked because the EnKF cannot take a masked
observation at more than one quantity.

## Reproducibility

Environment and dependencies are pinned in `analysis/pyproject.toml` and
`analysis/uv.lock` (`epymorph==2.0.0b1`, Python 3.12). A fixed seed reproduces a run byte
for byte on the same platform, whether it runs alone or in a parallel worker.

Initial conditions are drawn per node from a stream keyed on FIPS, so dropping a state from
the roster does not change any surviving node's values, and all three models get the same
state-level values at a given seed.

The ACS population and commuting inputs are frozen in `data/raw/` with their provenance,
so nothing here needs a Census API key.

The correlated-OU sensitivity analysis that used to live here (four more models with
spatially correlated parameter shocks) was removed in restructure step 4; it is not in the
manuscript. Its code and runs are in the maintainer's working folder.

## Where the reasoning lives

These are in the maintainer's working folder, not in this repository:

- `demo-covid/old/ifr-methods.md`: the infection fatality ratio and how it was derived
- `demo-covid/old/covid-v03.ipynb`: where the model, the data alignment and the seeding
  were worked out, including the runnable reproduction of the masked-observation limit
- `demo-covid/refactor-plan-v01.md`: the package's structure before the restructure
- `project-notes/handoff.md`: ensemble size, the window fix, the seeding defects, and
  the results of every run
- `bug-reports/epymorph-facility-hospitalization-statescope.ipynb`: the masked
  `StateScope` result
- `correlated-ou/`: the removed sensitivity analysis
