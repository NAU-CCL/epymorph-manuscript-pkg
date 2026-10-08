"""The two demonstration vignettes for the epymorph 2.0 manuscript.

Both ask the same question of different added structure: **does it buy forecast skill?**
Demo 1 (`flu`) asks it of demographic structure, Demo 2 (`covid`) of spatial structure and
movement. The three models within each demo differ only in data, never in code, which is
the claim the manuscript rests on.

The demos themselves are `manuscript_analysis/demo-flu.ipynb` and `demo-covid.ipynb`
(restructure steps 4-6). What is left here until step 7 flattens the layout:

- `paths.py` — where the runs, tables and figures live.
- `manifest.py` — the checksums of the runs, `results/demos/MANIFEST.sha256`.
"""
