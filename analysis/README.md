# analysis

All executable code: the `manuscript_analysis` package, whose two notebooks are the case
studies, and the build that runs them.

## Setup

    just setup        # or: cd analysis && uv sync

One environment, pinned by `pyproject.toml` and `uv.lock` (`epymorph==2.0.0b1`, Python
3.12). Installing the package is what lets a notebook `import manuscript_analysis` from
anywhere, with no `sys.path` inserts.

No API key is needed to build or check anything: the CDC surveillance series are frozen in
`data/demos/` (they are revised weekly, so re-fetching them would move the target the
models are scored against), and the Census and contact-matrix inputs in `data/raw/`, each
with a provenance record (`manuscript_analysis/data.py`). A free Census API key in a
`.env` at the repository root (copy `.env.example`) is needed only to refresh a frozen
input; the `just` recipes load it.

## What is here

`manuscript_analysis/`

- `demo-flu.ipynb`, `demo-covid.ipynb` -- the two case studies, each top to bottom: the
  data, the models in epymorph, one fit and forecast explained, the rolling forecasts of
  every model at both seeds, and the scores, figures and tables. Edit them directly; they
  are committed without outputs.
- `demo-flu.md`, `demo-covid.md` -- what to know about each: the models, the season, the
  data and its quirks, and where the reasoning behind the design lives.
- `__main__.py` -- the build, `python -m manuscript_analysis` (`just build`): the search,
  then each notebook through papermill, then the checksums. `--runs-dir` reads and fits
  the runs somewhere other than `results/demos/runs/`.
- `flu_inputs.py`, `covid_inputs.py` -- each case study's data preparation that is not
  epymorph.
- `runs.py`, `scoring.py`, `plots.py`, `util.py` -- writing and reading runs, scoring,
  drawing a panel, writing a table and checking outputs; shared by both notebooks.
- `data.py` -- `ProvenanceCachedADRIO`, which freezes an ADRIO's result in `data/raw/`.
- `ADDING-FIGURES.md` -- how a figure gets into the paper.
- `lit_search/` -- the software-landscape search pipeline. See its own README.

## Conventions

- **Readable over clever.** This code is read by people learning epymorph. Explicit loops
  and named intermediates beat dense one-liners.
- **The notebooks demonstrate epymorph; the modules beside them hide everything else.**
  Anything that touches the epymorph API belongs where a reader will see it; the plotting
  and data-wrangling beneath it belongs in a module.
- **`plots.py` draws a panel; the notebook lays out the figure.** See `ADDING-FIGURES.md`.
- **Never hand-edit a generated file.** Every generated `.tex` carries a `% GENERATED`
  header; `just check` enforces it.
- **Run `just check` before and after a change.** It is the regression suite.
- **Do not casually delete `results/demos/runs/`.** It is ~1 GB and about five hours to
  rebuild.
- **No em-dashes in manuscript prose.** Code comments are fine.
- **Name things for what they are.** An *ensemble* is the filter's realizations (300 for
  flu, 600 for COVID); a *run* is one model at one seed. Not "arm" (clinical trials) or
  "ablation" (machine learning) for the model comparison; the models have names.

## Running things

From the repository root:

    just build      # the search, then both notebooks: minutes with the runs, ~5 h without
    just check      # everything checkable, ~4 min
    just notebooks  # JupyterLab, for reading or running a notebook interactively

    uv run --project analysis python -m manuscript_analysis.lit_search --check   # the search alone

A quick run of a whole notebook, over only its first three forecast dates, with its runs
fitted into a scratch folder and nothing written to `results/` (about 15 minutes for
COVID; flu's stratified models take about 50):

    cd analysis/manuscript_analysis
    uv run papermill demo-covid.ipynb /tmp/out.ipynb -p runs_dir /tmp/runs -p max_forecast_dates 3
