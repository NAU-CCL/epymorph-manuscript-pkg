"""Demo 2: does spatial structure and movement buy forecast skill?

Three COVID models over the 2020-21 season, identical but for geography and movement: 32 counties with ACS commuting flows, the same counties with no movement, or 3 states with no spatial resolution.

The models and their runs are in `manuscript_analysis/demo-covid.ipynb`. `evaluation.py`
loads, scores and draws the runs; `geography.py` serves it the frozen geography until
restructure step 5 moves the evaluation into the notebook.
"""
