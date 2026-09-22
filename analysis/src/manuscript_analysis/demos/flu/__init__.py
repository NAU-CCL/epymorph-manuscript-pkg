"""Demo 1: does demographic structure buy forecast skill?

Three influenza models over the FluSight 2025-26 challenge period, identical but for their contact structure: the Mistry et al. empirical contact matrix, contact in proportion to group size, or no age structure at all.

`models/` holds the model definitions and the season's shared setup; `seasons.py` says
what is forecast and over what window; `evaluation.py` loads, scores and draws.
"""
