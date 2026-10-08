# analysis

The Python sub-project for all executable code: the reusable `manuscript_analysis`
package, the driver notebooks that call it, and the tests.

## Setup

    cd analysis && uv sync

One environment, pinned by `pyproject.toml` and `uv.lock`. Installing the package is what
lets a notebook `import manuscript_analysis` from anywhere, with no `sys.path` inserts.

No API key is needed to build or check anything: the CDC surveillance series are frozen in
`data/demos/` (they are revised weekly, so re-fetching them would move the target the
models are scored against), and the Census and contact-matrix inputs in `data/raw/`, each
with a provenance record (`src/manuscript_analysis/data.py`). A free Census API key in a
`.env` at the repository root (copy `.env.example`) is needed only to refresh a frozen
input, or for the `01` notebooks, which fetch live to show how.

## What is here

`src/manuscript_analysis/`

- `demos/` -- the two demonstration vignettes. `lib/` is everything not specific to one
  demo (the forecasting loop, scoring, plotting, IPMs); `flu/` and `covid/` are each
  demo's season, models and evaluation; `export.py` and `tables.py` build the
  manuscript's figures and tables; `paths.py` says where everything lives.
- `lit_search/` -- the software-landscape search pipeline. See its own README.

`src/manuscript_analysis/demos/ADDING-FIGURES.md` -- how to add a figure, and which of
the three places it belongs in. Read it before changing `export.py`.

`src/manuscript_analysis/demo-covid.ipynb` -- Demo 2, top to bottom: the data, the
models in epymorph, one fit and forecast explained, the rolling forecasts of every model
at both seeds, and the scores, figures and tables. Its data preparation is in
`covid_inputs.py`; `runs.py`, `scoring.py`, `plots.py` and `util.py` (writing tables)
serve both demos. Demo 1 follows the same shape in restructure step 6.

`notebooks/demo-flu/`, `notebooks/demo-covid/` -- the rest of the readable surface.
Demo 1's `01-model-and-forecast.ipynb` builds its models in epymorph and runs one fit and
one forecast, with every epymorph call in view; its `02-evaluation.ipynb` renders the
manuscript's Demo 1 tables and figures from the runs. These are hand-maintained; edit them
directly.

## Conventions

- **Readable over clever.** This code is read by people learning epymorph. Explicit loops
  and named intermediates beat dense one-liners.
- **The notebooks demonstrate epymorph; `demos/lib/` hides everything else.** Anything
  that touches the epymorph API belongs where a reader will see it; the plotting and
  data-wrangling beneath it belongs in the library.
- **Panels draw, `export.py` lays out.** See
  `src/manuscript_analysis/demos/ADDING-FIGURES.md`, which also has the naming rule.
- **Never hand-edit a generated file.** Every generated `.tex` carries a `% GENERATED`
  header; `../scripts/check.sh` enforces it.
- **Run `../scripts/check.sh` before and after a change.** It is the regression suite.
- **Do not casually delete `results/demos/runs/`.** It is ~1 GB and 8-10 hours to rebuild.
- **No em-dashes in manuscript prose.** Code comments are fine.
- **Name things for what they are.** Not "arm" (clinical trials) or "ablation" (machine
  learning) for the model comparison; the models have names.

## Running things

    python -m manuscript_analysis.lit_search --check     # the search pipeline
    ../scripts/run-demos.sh                              # the ensembles, ~8-10 h
    ../scripts/build-figures.sh                          # figures + tables, ~2 min
    ../scripts/check.sh                                  # everything checkable

One model on its own, for a quick look:

    python -m manuscript_analysis.demos.flu.run_season models.single_strata -n 20
