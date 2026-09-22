"""Demo 2: does spatial structure and movement buy forecast skill?

Three COVID models over the 2020-21 season, identical but for geography and movement: 32 counties with ACS commuting flows, the same counties with no movement, or 3 states with no spatial resolution.

`models/` holds the model definitions and the season's shared setup; `seasons.py` says
what is forecast and over what window; `evaluation.py` loads, scores and draws.
"""
