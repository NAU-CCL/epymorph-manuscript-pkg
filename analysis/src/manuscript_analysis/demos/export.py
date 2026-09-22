"""Compose the manuscript's multi-panel figures from the two demos' panel functions.

Phase 6 of the demo plan. Every panel here is drawn by a `figure_*` in
`demo-flu/evaluation.py` or `demo-covid/evaluation.py`, the same functions the notebooks
call, so a figure in the paper and the same figure in a notebook cannot disagree. This
file contributes **layout only**: which panels, in what grid, with what letters. If a
panel needs different content, change it in that demo's `evaluation.py`, not here.

Agreed 2026-09-21 with JM, revising `drafts/figure-plan-v01.md`. **The two figures have
the same four panels**, which is the point: one argument run twice, along different axes.

| | meaning | Figure 2 (flu) | Figure 3 (covid) |
|---|---|---|---|
| (a) | what varies between the models | contact structures | commuting matrix |
| (b) | forecast skill against horizon | 3 models | 3 models x 2 quantities |
| (c) | the model fitting its own many channels | 6 age bands | 3 counties x 2 quantities |
| (d) | the benefit, distributed over units | 51 jurisdictions | 32 counties |

Panel (c) is the one JM asked for on 2026-09-21 and it is why the arrangement changed:
neither figure previously showed the model fitting more than one channel, which is the
capability the structured models exist to demonstrate. It displaced the forecast-fan
panels (Demo 1's rolling forecasts, Demo 2's state fit) to the supplement, where the
notebooks already save them.

Panel (d) is drawn at the **finest** resolution each demo has, which for Demo 2 means
counties rather than the three scored states: pooling 32 partly-independent nodes cancels
exactly the noise the movement model represents.

**Calibration is supplementary**, so the main text is Figures 1-3 plus Box 1. Figure 1 is
the designer's system diagram and is not produced here.

The supplementary figures this file also builds:

- **calibration**, both demos side by side.
- **rolling forecasts**, one figure per demo, each showing the same forecasts at the
  model's own resolution and at the scale they are scored. One per demo rather than one
  combined, because four rows of six panels runs past a page.

The forecast fans over-predict during growth phases. That is why they are supplementary:
the paper's claim is comparative and every main-text panel is, whereas a fan plot is
absolute performance and invites the models to be judged as forecasters rather than as a
controlled comparison. The text states the over-prediction rather than leaving a reviewer
to find it.

Usage:

    python export_manuscript.py                  # everything, into figures/
    python export_manuscript.py --figures-dir DIR
    python export_manuscript.py --only figure-2
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from manuscript_analysis.demos import paths
from manuscript_analysis.demos.covid import evaluation as covid
from manuscript_analysis.demos.flu import evaluation as flu
from manuscript_analysis.demos.lib.figures import (
    DOUBLE_COLUMN,
    FINE_SCALE,
    label_panels,
    save_figure,
    use_manuscript_style,
)

OUTPUT_DIR = paths.FIGURES
"""Where the composed figures land. See `manuscript_analysis.demos.paths`."""


# --- Figure 2: Demo 1, does demographic structure buy forecast skill? --------------

FLU_MODEL = "multi-strata-empirical"
"""The model panel (c) fits. Panels (b) and (d) show all three.

Which *places* the figures draw is not here: `demo-flu/evaluation.FOCUS_STATE` and
`REFERENCE_STATES` hold that, and the notebook reads the same two, so iterating on them
moves the paper and the notebook together. Demo 2's equivalent is `focus_counties`.
"""


def figure_2_flu(ev, replicate):
    """Figure 2: four panels in three rows, the same four Figure 3 has.

    Panel (d) is the headline. Pooled WIS, which is what panel (b) shows, is dominated by
    the four largest states, so the distribution over jurisdictions is both the stronger
    statistic and the more honest one, and it is the only panel that draws both seeds.
    """
    fig = plt.figure(figsize=(DOUBLE_COLUMN, 8.3), layout="constrained")
    top, channels, benefit = fig.subfigures(3, 1, height_ratios=[2.5, 3.4, 2.4])
    structure, skill = top.subfigures(1, 2, width_ratios=[1.9, 1.0])

    flu.figure_contact_structures(flu.FOCUS_STATE, title=None, subfig=structure)
    # An in-axes legend: this panel is half a row wide, and matplotlib places an
    # "outside" legend against the parent figure rather than against the subfigure.
    flu.figure_wis_by_horizon(ev, subfig=skill, legend="axes")
    flu.figure_fit_by_age(
        ev, flu.FOCUS_STATE, FLU_MODEL, title=None, subfig=channels
    )
    flu.figure_relative_wis_swarm(ev, replicate, title=None, subfig=benefit)

    label_panels([structure, skill, channels, benefit])
    return fig


# --- Figure 3: Demo 2, does spatial structure and movement buy forecast skill? -----

COVID_FIT_MODEL = "movement"
"""Panel (c) draws the movement model at its own counties, not at the scored states.

This is the parallel to Figure 2(c): the model fitting many channels rather than one.
It has to be a county model, because the three scored states are exactly where the county
structure has been summed away; and it can only be shown at the model's own nodes, because
the fit is stored as quantiles and quantiles do not add. See
`demo-covid/evaluation.figure_fit`.
"""


def figure_3_covid(ev, replicate):
    """Figure 3: the same four panels as Figure 2, lettered to mean the same things.

    (a) and (b) share a row because the commuting matrix is square and would otherwise
    waste half a row. Reading order is still (a) (b) (c) (d).
    """
    fig = plt.figure(figsize=(DOUBLE_COLUMN, 8.3), layout="constrained")
    top, channels, benefit = fig.subfigures(3, 1, height_ratios=[2.9, 3.4, 2.0])
    structure, skill = top.subfigures(1, 2, width_ratios=[1.0, 1.3])

    covid.figure_movement_structure(title=None, subfig=structure)
    covid.figure_wis_by_horizon(ev, subfig=skill, legend="axes")
    covid.figure_fit(
        ev, COVID_FIT_MODEL, locations=covid.focus_counties(),
        title=None, subfig=channels,
    )
    covid.figure_county_relative_wis(ev, replicate, title=None, subfig=benefit)

    label_panels([structure, skill, channels, benefit])
    return fig


# --- Supplementary: calibration across both demos ---------------------------------


def figure_s_calibration(flu_ev, covid_ev, nominal: float = 0.95):
    """Interval coverage against nominal, both demos side by side.

    Supplementary by JM's call, 2026-09-21. It still carries a real methodological
    point: Demo 2's two spatial scales miss in *opposite* directions, because
    aggregating partly-independent nodes cancels noise that a single node retains, which
    makes WIS an awkward adjudicator between forecasts at different spatial scales.

    Two legends rather than one: the demos' models have the same colour roles but
    different names, so a shared legend would be wrong rather than merely crowded. They
    go *inside* the panels (`legend="axes"`): matplotlib places an "outside" legend
    against the parent figure, so two side-by-side subfigures would stack theirs on top
    of each other.
    """
    fig = plt.figure(figsize=(DOUBLE_COLUMN, 2.9), layout="constrained")
    left, right = fig.subfigures(1, 2, width_ratios=[1.0, 2.0])
    flu.figure_calibration(flu_ev, nominal=nominal, subfig=left, legend="axes")
    covid.figure_calibration(covid_ev, nominal=nominal, subfig=right, legend="axes")
    label_panels([left, right])
    return fig


def figure_s_flu_forecasts(ev):
    """Supplementary: Demo 1's rolling forecasts at both resolutions.

    (a) the six age bands the model actually forecasts, for one state; (b) the state
    totals those bands are summed into, which is what every score is computed on. Reading
    down is the aggregation the demo performs: summed **inside each realization**, before
    any quantile is taken, because quantiles do not add.

    `evaluation.FOCUS_STATE` leads `REFERENCE_STATES`, so it appears in both rows and one
    state can be traced from its bands to its total. The upper row is drawn in
    `manuscript_analysis.demos.lib.figures.FINE_SCALE`, a darker shade of the same blue, so two resolutions of
    one model do not read as two models.

    The fans over-predict during the growth phase, in both demos and at both resolutions.
    That is a real limitation of these models rather than a drawing artifact, and it is
    why this figure is supplementary and stated in the text rather than shown as a
    main-text result: the paper's claim is comparative, and every main-text panel is.
    """
    fig = plt.figure(figsize=(DOUBLE_COLUMN, 5.8), layout="constrained")
    channels, aggregate = fig.subfigures(2, 1, height_ratios=[3.4, 2.2])

    # The darker shade marks the model's own resolution, so the two rows cannot be read
    # as two models. See `manuscript_analysis.demos.lib.figures.FINE_SCALE`.
    flu.figure_rolling_forecasts_by_age(
        ev, flu.FOCUS_STATE, FLU_MODEL, title=None, subfig=channels, color=FINE_SCALE,
    )
    flu.figure_rolling_forecasts(
        ev, flu.focus_states(ev), FLU_MODEL, title=None, subfig=aggregate
    )
    label_panels([channels, aggregate])
    return fig


def figure_s_covid_forecasts(ev):
    """Supplementary: Demo 2's rolling forecasts at both resolutions.

    (a) the counties the model forecasts, (b) the states those counties are summed into
    and scored at. The **columns correspond**: each county in (a) is the largest county
    of the state directly below it, so a column is one place at two resolutions.

    This is the figure behind the methodological point in `figure_calibration`: summing
    partly-independent nodes cancels noise that a single node retains, so the county rows
    are both wider and more biased than the state rows beneath them. The county rows are
    drawn in `manuscript_analysis.demos.lib.figures.FINE_SCALE` for the same reason as Demo 1's.
    """
    fig = plt.figure(figsize=(DOUBLE_COLUMN, 7.6), layout="constrained")
    counties, states = fig.subfigures(2, 1, height_ratios=[1.0, 1.0])

    covid.figure_rolling_forecasts(
        ev, COVID_FIT_MODEL, locations=covid.focus_counties(),
        title=None, subfig=counties, color=FINE_SCALE,
    )
    covid.figure_rolling_forecasts(ev, COVID_FIT_MODEL, title=None, subfig=states)
    label_panels([counties, states])
    return fig


# --- Driver -----------------------------------------------------------------------

FIGURES = (
    "figure-2",
    "figure-3",
    "figure-s-calibration",
    "figure-s-flu-forecasts",
    "figure-s-covid-forecasts",
)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--figures-dir", type=Path, default=OUTPUT_DIR,
        help=f"where to write; default {OUTPUT_DIR}",
    )
    parser.add_argument(
        "--only", choices=FIGURES, action="append",
        help="build one figure; repeatable. Default: all of them.",
    )
    args = parser.parse_args(argv)
    wanted = set(args.only or FIGURES)

    use_manuscript_style()
    written = []

    flu_ev = flu.load()
    flu_replicate = flu.load_replicate()
    if "figure-2" in wanted:
        fig = figure_2_flu(flu_ev, flu_replicate)
        written += save_figure(fig, "fig2-flu-demographic-structure", args.figures_dir)
        plt.close(fig)
    if "figure-s-flu-forecasts" in wanted:
        fig = figure_s_flu_forecasts(flu_ev)
        written += save_figure(fig, "figS-flu-rolling-forecasts", args.figures_dir)
        plt.close(fig)

    covid_ev = covid.load()
    covid_replicate = covid.load_replicate()
    if "figure-3" in wanted:
        fig = figure_3_covid(covid_ev, covid_replicate)
        written += save_figure(fig, "fig3-covid-spatial-structure", args.figures_dir)
        plt.close(fig)
    if "figure-s-covid-forecasts" in wanted:
        fig = figure_s_covid_forecasts(covid_ev)
        written += save_figure(fig, "figS-covid-rolling-forecasts", args.figures_dir)
        plt.close(fig)

    if "figure-s-calibration" in wanted:
        fig = figure_s_calibration(flu_ev, covid_ev)
        written += save_figure(fig, "figS-calibration-both-demos", args.figures_dir)
        plt.close(fig)

    for path in written:
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
