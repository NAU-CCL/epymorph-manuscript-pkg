# analysis

All the executable code, including the `manuscript_analysis` package and the two case-study
notebooks. Run every command below from the repository root.

## Environment

```bash
just setup        # or: cd analysis && uv sync
```

The environment is pinned by `pyproject.toml` and `uv.lock` (`epymorph==2.0.0b1`, Python
3.12). Because the package is installed, a notebook can `import manuscript_analysis` from
anywhere.

## What is here

`manuscript_analysis/`:

| file | what it does |
|---|---|
| `demo-flu.ipynb`, `demo-covid.ipynb` | the two case studies. |
| `__main__.py` | the build (`just build`): the literature search, each notebook through papermill, then the checksums. `--runs-dir` puts the runs somewhere else |
| `flu_inputs.py`, `covid_inputs.py` | each case study's data preparation scipt that does not use epymorph |
| `runs.py` | writes a run to disk, checks whether one is already there, reads it back |
| `scoring.py` | the weighted interval score (WIS), interval coverage and relative WIS |
| `plots.py` | custom plotting utils. draws each panel of a figure separately|
| `util.py` | writing a table as LaTeX, and checking regenerated outputs against the committed ones |
| `data.py` | `ProvenanceCachedADRIO`: freezes an ADRIO's result in `data/raw/` with a provenance record |
| `fetch_flu_observations.py`, `fetch_covid_observations.py` | how the frozen CDC observations were made. `just fetch-observations <folder>` fetches fresh copies into a new folder and compares them with the frozen ones. |
| `lit_search/` | the software literature search (see below) |

## The case studies

Each notebook asks whether one kind of model structure improves forecast skill. It builds
three models that differ only in their data, explains one fit and forecast step by step,
runs every model at seeds 0 and 1, scores the runs, and generates the manuscript's figures and
tables. If run interactively, a notebook shows its figures and tables but writes nothing to disk.
`just build`, however, gives a notebook an `output_dir`, and then it writes to `results/demos/`. The build reuses a run that is already on disk with the same settings and fits any that are missing.

### Demo 1: influenza and age structure (`demo-flu.ipynb`)

| model | structure | fitting time |
|---|---|---|
| `multi-strata-empirical` | six age groups, mixing by the Mistry et al. contact matrix projected onto each state's age distribution | ~3-4 h |
| `multi-strata-homogeneous` | six age groups, contact in proportion to the population size of each age group | ~3-4 h |
| `single-strata` | one homogenous population, no age stratification | ~25 min |

- **Season.** The 2025-26 influenza season across 51 jurisdictions. The simulation starts
  2025-09-13 and runs 38 weeks. After 10 burn-in weeks there are 25 forecast dates, from
  2025-11-22 to 2026-05-09, each forecasting four weeks ahead. The ensemble has 300
  realizations; at 100, the per-jurisdiction comparison did not reproduce across seeds.
- **Observations** (`data/demos/flu/observations.csv`) come from CDC's
  `CurrentStateAdmissions` (dataset `mpgq-jmmr`). That dataset is marked "Preliminary"
  and CDC revises it every Wednesday, which is why the file is frozen: a re-fetch two
  weeks later gave materially different results.
- **Age bands vs. all-ages total.** The six age bands sum to about 0.25% less than CDC's
  all-ages total. Models are fitted to the sum of the bands; the reported total is kept as
  a `total_reported` row for checking.
- **Puerto Rico** is forecast but left out of the scores (`UNSCORED` in the notebook). This follows the conventions of FluSight.

### Demo 2: COVID-19 and movement (`demo-covid.ipynb`)

| model | structure | fitting time |
|---|---|---|
| `movement` | 32 counties in MA, CT and NH, with ACS commuting flows between them | ~86 min |
| `county` | the same 32 counties, with no movement between them | ~35 min |
| `state` | the 3 states, one node each | ~9 min |

- **Season.** The simulation starts Sunday 2020-08-09 and runs 35 weeks. After 8 burn-in
  weeks there are 24 forecast dates, from 2020-10-04 to 2021-03-14, each forecasting four
  weeks ahead. The ensemble has 600 realizations. The start must be a Sunday, because the
  two CDC series label a week by opposite ends.
- **Observations** (`data/demos/covid/observations.csv`) are two weekly quantities per
  county, fitted jointly under one likelihood:
  - hospital census, from `COVIDFacilityHospitalization`, averaged over the week. Its
    dataset (`anag-cw7u`) is served from healthdata.gov, not data.cdc.gov. It is fetched
    at county scope and summed to states, because at `StateScope` the ADRIO returns an
    entirely masked result.
  - deaths, from `CountyDeaths` (`ite7-j2w7`), summed over the week.
- **Suppressed deaths.** 41.2% of county-week death counts are suppressed for privacy.
  They are imputed with a fixed seed, by a truncated-Poisson draw at the region's own
  per-capita death rate that week: 1,762 deaths across the season. These sources are no longer revised, and on 2026-10-08 the fetch
  script reproduced the frozen file byte for byte.
- **Initial conditions** are drawn per node from a random stream keyed on its FIPS code.
  All three models therefore get the same state-level values at a given seed, and
  dropping a state does not change any other node's values.

### Frozen inputs

Nothing in a build calls the Census API or CDC. The CDC series are frozen in
`data/demos/`, and loading stops with an error if a file is missing or does not cover the
season. The Census inputs (population, population by age, commuting flows) and the Mistry
contact matrix are frozen in `data/raw/`. Each file there has a `.provenance.json` beside
it, recording what it is, when it was frozen and a SHA-256 of its contents, and every
read checks the file against that record. File names include the ACS vintage and the
states.

To refresh a Census input on purpose, delete the file and its `.provenance.json`, put a
Census API key in `.env`, and run the notebook  through `just notebooks` or
`just build`. Those recipes load `.env`.

The one thing a build downloads is the Census TIGER geography that epymorph uses to build
a `StateScope` or `CountyScope`.

### Quick test of a notebook

To run a whole notebook over only its first three forecast dates, with the runs in a
scratch folder and nothing written to `results/` (about 15 minutes for COVID, 50 for flu):

```bash
cd analysis/manuscript_analysis
uv run papermill demo-covid.ipynb /tmp/out.ipynb -p runs_dir /tmp/runs -p max_forecast_dates 3
```

## Adding a figure

**A figure in the paper must be one that `just build` produces.** A figure someone saved
by hand cannot be regenerated or checked.

| you want to... | put it |
|---|---|
| look at something | in a notebook cell that ends in `plt.show()` |
| draw a new kind of panel | in a new function in `plots.py` |
| put a figure in the paper | in a cell in section 9 of the notebook that ends in `save(fig, name)` |

In the notebook, each panel is a small
`draw_<what>(subfig, ...)` function that selects the data and calls `plots.py`, and the
figure is a few lines of layout. 

To add one:

1. Write the cell in the notebook. Name the figure `fig<n>-<demo>-<what>` for the main text
   or `figS-<what>` for the supplement.
2. Run `just build`, then `just check`. The build pins
   `PYTHONHASHSEED`, without which a PDF's bytes change from run to run.
3. Commit the PDF, the PNG and `results/checksums.sha256` together.
4. Run `just publish --apply`, then use `\includegraphics{figures/<name>.pdf}` in
   Overleaf.

If a new figure replaces an old one, delete the old PDF and PNG from
`results/demos/figures/` and from Overleaf manually.

## The literature search (`lit_search/`)

The structured search behind Appendix S1, Table 1 and the candidate register.
`just build` runs it first, and `just check` runs it with its checks. To run it alone:

```bash
uv run --project analysis python -m manuscript_analysis.lit_search           # run the pipeline
uv run --project analysis python -m manuscript_analysis.lit_search --check   # and verify the manuscript
```

It follows the repository's layering, set out in `paths.py`:

| directory | written by |
|---|---|
| `data/lit-search/raw/` | nobody. The PubMed and Lens.org exports from July 2026, plus `queries-as-executed.md`, the exact queries that produced them. They cannot be re-fetched, since the same query returns more records every month, and `results/lit-search/MANIFEST.sha256` checks them on every run |
| `data/lit-search/decisions/` | a person. The screening decisions, Table 1's marks and the register's rows. No code writes here |
| `results/lit-search/` | the pipeline, only |

How it works: `lexicon.py` defines one set of search terms, applied unchanged to both
sources. A record advances if all three concept blocks match its title, abstract or
keywords; 645 of 3,033 records do. The records the screen sets aside are then audited for
missed packages.

`--check` verifies that:

1. every count the manuscript quotes from the search matches the pipeline (the phrases
   are matched in `report.py`; update them if the prose is reworded);
2. Appendix S1 lists every term the screen uses;
3. every advanced record has a decision and a reason;
4. the decisions use only the vocabulary in `decisions/screen-decisions-codebook.md`,
   which `validate_decisions.py` reads directly;
5. every package's `bib_key` and DOI match `references.bib`;
6. Table 1 matches `decisions/table-marks.csv` cell for cell;
7. the register workbook rebuilds byte for byte;
8. the archived exports have not changed.

To change a decision, edit the CSVs in `data/lit-search/decisions/`; the codebook says
what each column may hold. Never edit `results/lit-search/software-candidate-register.xlsx`
directly, because `register.py` rebuilds it.
