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
input.

## What is here

`src/manuscript_analysis/`

- `demo-flu.ipynb`, `demo-covid.ipynb` -- the two case studies, each top to bottom: the
  data, the models in epymorph, one fit and forecast explained, the rolling forecasts of
  every model at both seeds, and the scores, figures and tables. Edit them directly; they
  are committed without outputs.
- `flu_inputs.py`, `covid_inputs.py` -- each demo's data preparation that is not epymorph.
- `runs.py`, `scoring.py`, `plots.py`, `util.py` -- writing and reading runs, scoring,
  drawing a panel, writing a table; shared by both demos.
- `data.py` -- `ProvenanceCachedADRIO`, which freezes an ADRIO's result in `data/raw/`.
- `demos/` -- `paths.py` and `manifest.py` (the run checksums), until restructure step 7.
- `lit_search/` -- the software-landscape search pipeline. See its own README.

`notebooks/demo-flu/README.md`, `notebooks/demo-covid/README.md` -- each demo's design,
data and where the reasoning lives.

## Conventions

- **Readable over clever.** This code is read by people learning epymorph. Explicit loops
  and named intermediates beat dense one-liners.
- **The notebooks demonstrate epymorph; the modules beside them hide everything else.**
  Anything that touches the epymorph API belongs where a reader will see it; the plotting
  and data-wrangling beneath it belongs in a module.
- **`plots.py` draws a panel; the notebook lays out the figure.**
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

A quick look at a demo, over its first three forecast dates, into a scratch folder:

    cd src/manuscript_analysis
    python -m papermill demo-flu.ipynb /tmp/out.ipynb -p runs_dir /tmp/runs -p max_forecast_dates 3
