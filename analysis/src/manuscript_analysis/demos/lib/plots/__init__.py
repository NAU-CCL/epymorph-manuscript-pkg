"""Plotting helpers for the manuscript demos.

These functions are deliberately epymorph-agnostic: they take plain numpy or
pandas objects. The notebooks stay responsible for the epymorph-side work
(selecting quantities, munging pipeline output), which is what we want readers
to see; the matplotlib fiddling lives here.

**Both demos draw the same figures from the same functions.** The demos differ in what a
panel means, never in how it is drawn, which is what lets the manuscript claim the models
differ by data rather than by code. The map, Demo 1 (`demo-flu/evaluation.py`) against
Demo 2 (`demo-covid/evaluation.py`):

| here | Demo 1 uses it for | Demo 2 uses it for |
|---|---|---|
| `plot_quantile_grid` | `figure_fit_by_age` (6 age bands over 2x3), `figure_eta_by_age` | `figure_fit` (quantity by node) |
| `plot_rolling_forecast_grid` | `figure_rolling_forecasts`, `figure_rolling_forecasts_by_age` | `figure_rolling_forecasts`, at either scale |
| `plot_line_panels` | `figure_wis_by_horizon`, `figure_calibration` (1 panel) | the same two (2 panels, one per quantity) |
| `plot_single_forecast_grid` | `01-model-and-forecast.ipynb`: one origin, three models | the same |
| `plot_ratio_swarm` | `figure_relative_wis_swarm` (51 jurisdictions) | `figure_county_relative_wis` (32 counties) |
| `panel_grid` | the swarm's single axes | the swarm's, and `figure_relative_wis` |
| `plot_contact_matrix` / `plot_flow_matrix` | `figure_contact_structures` | `figure_movement_structure` |

The two matrix figures are the deliberate exception: a 6x6 annotated contact matrix and a
32x32 log-scaled flow matrix are the same *panel role* (what varies between the models,
drawn as panel (a) of both figures) but not the same drawing.

The grids in `layout.py` are where the shared typesetting rules live: dates under the
bottom row only, y labels on the first column, one legend for the figure.
"""

from manuscript_analysis.demos.lib.plots.distributions import (
    plot_ratio_swarm,
    swarm_offsets,
)
from manuscript_analysis.demos.lib.plots.layout import (
    as_panel_rows,
    finish_panel_grid,
    panel_grid,
)
from manuscript_analysis.demos.lib.plots.matrices import (
    plot_contact_matrix,
    plot_flow_matrix,
)
from manuscript_analysis.demos.lib.plots.timeseries import (
    plot_forecast_fan,
    plot_line_panels,
    plot_observations,
    plot_quantile_bands,
    plot_quantile_bars,
    plot_quantile_grid,
    plot_quantile_panels,
    plot_rolling_forecast_grid,
    plot_rolling_forecasts,
    plot_single_forecast_grid,
)

__all__ = [
    "as_panel_rows",
    "finish_panel_grid",
    "panel_grid",
    "plot_contact_matrix",
    "plot_flow_matrix",
    "plot_forecast_fan",
    "plot_line_panels",
    "plot_observations",
    "plot_quantile_bands",
    "plot_quantile_bars",
    "plot_quantile_grid",
    "plot_quantile_panels",
    "plot_ratio_swarm",
    "plot_rolling_forecast_grid",
    "plot_rolling_forecasts",
    "plot_single_forecast_grid",
    "swarm_offsets",
]
