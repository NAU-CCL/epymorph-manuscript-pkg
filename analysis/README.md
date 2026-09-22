# analysis

The Python sub-project for all executable code: the reusable `manuscript_analysis`
package, the driver notebooks that call it, and the tests.

## Setup

    cd analysis && uv sync

One environment, pinned by `pyproject.toml` and `uv.lock`. Installing the package is what
lets a notebook `import manuscript_analysis` from anywhere, with no `sys.path` inserts.

The demography and commuting ADRIOs need a free Census API key in a `.env` at the
repository root; copy `.env.example`. The CDC surveillance data does **not** need one,
because it is frozen in `data/demos/` -- those series are revised weekly, so re-fetching
them would move the target the models are scored against.

## What is here

`src/manuscript_analysis/`

- `demos/` -- the two demonstration vignettes. `lib/` is everything not specific to one
  demo (the forecasting loop, scoring, plotting, IPMs); `flu/` and `covid/` are each
  demo's season, models and evaluation; `export.py` and `tables.py` build the
  manuscript's figures and tables; `paths.py` says where everything lives.
- `lit_search/` -- the software-landscape search pipeline. See its own README.

`src/manuscript_analysis/demos/ADDING-FIGURES.md` -- how to add a figure, and which of
the three places it belongs in. Read it before changing `export.py`.

`notebooks/demo-flu/`, `notebooks/demo-covid/` -- the exploratory surface: run the models,
load and score them, draw every panel, and render the composed manuscript figures. These
are hand-maintained and have no generator; edit them directly.

## Running things

    python -m manuscript_analysis.lit_search --check     # the search pipeline
    ../scripts/run-demos.sh                              # the ensembles, ~8-10 h
    ../scripts/build-figures.sh                          # figures + tables, seconds
    ../scripts/check.sh                                  # everything checkable

One model on its own, for a quick look:

    python -m manuscript_analysis.demos.flu.run_season models.single_strata -n 20
