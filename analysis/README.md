# analysis

The Python sub-project for all executable code: the reusable `manuscript_analysis` package
plus the driver notebooks that call it.

`src/manuscript_analysis/lit_search/` is populated: the software-landscape search pipeline,
moved here 2026-09-21. It runs without an install, because each module resolves its own
imports:

    python3 -m manuscript_analysis.lit_search --check
    python3 analysis/src/manuscript_analysis/lit_search/__main__.py --check

See its own README for the three-layer rule it is built on and what each check does.

`pyproject.toml`, `uv.lock`, `.python-version`, and the rest of `src/manuscript_analysis/`
arrive from the old `demolib/` folder in the next migration step; `notebooks/demo-flu/` and
`notebooks/demo-covid/` in the step after that.
