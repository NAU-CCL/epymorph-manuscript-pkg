"""The two demonstration vignettes for the epymorph 2.0 manuscript.

Both ask the same question of different added structure: **does it buy forecast skill?**
Demo 1 (`flu`) asks it of demographic structure, Demo 2 (`covid`) of spatial structure and
movement. The three models within each demo differ only in data, never in code, which is
the claim the manuscript rests on.

- `lib/` — everything not specific to one demo: the forecasting loop, scoring, plotting,
  IPMs and parameter functions. Was `demolib/` in the working folder.
- `flu/`, `covid/` — each demo's season definition, models, and its evaluation and figure
  functions.
- `export.py`, `tables.py` — the manuscript's figures and tables. Layout and presentation
  only; every number comes from a demo's own `evaluation` module.
- `paths.py` — where everything lives.
"""
