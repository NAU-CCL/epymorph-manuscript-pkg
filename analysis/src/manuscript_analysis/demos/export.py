"""Compose Demo 1's manuscript figures from its panel functions.

Demo 2's figures are made in `demo-covid.ipynb` (restructure step 5); Demo 1's move into
its own notebook in step 6, and this file goes in step 7. Every panel here is drawn by a
`figure_*` in `demo-flu/evaluation.py`, the same functions the notebook calls, so a figure in the paper and the same figure in a notebook cannot disagree. This
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

- **calibration**, one file per demo, which the supplement sets side by side as (a) and
  (b); this is (a).
- **rolling forecasts**, one figure per demo, each showing the same forecasts at the
  model's own resolution and at the scale they are scored. One per demo rather than one
  combined, because four rows of six panels runs past a page.

The forecast fans over-predict during growth phases. That is why they are supplementary:
the paper's claim is comparative and every main-text panel is, whereas a fan plot is
absolute performance and invites the models to be judged as forecasters rather than as a
controlled comparison. The text states the over-prediction rather than leaving a reviewer
to find it.

**Every score in these figures is log WIS**, and every ratio is relative log WIS, the
ratio of geometric means, as in CDC's FluSight evaluations. That is set in one place,
`manuscript_analysis.scoring.HEADLINE_SCALE`, which `load()` defaults to; nothing here names a scale.

Usage:

    python export_manuscript.py                  # everything, into figures/
    python export_manuscript.py --figures-dir DIR
    python export_manuscript.py --only figure-2
"""

import argparse
import shutil
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from manuscript_analysis.demos import paths
from manuscript_analysis.demos.flu import evaluation as flu
from manuscript_analysis.plots import (
    DOUBLE_COLUMN,
    FINE_SCALE,
    label_panels,
    save_figure,
    use_manuscript_style,
)

OUTPUT_DIR = paths.FIGURES
"""Where the composed figures land. See `manuscript_analysis.demos.paths`."""

PIXEL_TOLERANCE = 2
"""Out of 255, for `--check`. Matplotlib's drawing carries last-bit floating-point noise
from one process to the next, though every number computed here is bitwise stable; it
moves antialiased edges by at most 1/255 (measured 2026-10-07: 907 of 7.4 million pixels
in the calibration figure) and the tenth decimal of a PDF coordinate. Any real change to a
figure moves pixels by far more, so the check compares the PNGs' pixels within this
tolerance rather than bytes. The PDFs are the same drawing in vector form."""


def drifted_figures(fresh_dir: Path, committed_dir: Path) -> list[str]:
    """Each PNG in `fresh_dir` against the one on disk, pixel by pixel."""
    problems = []
    for fresh in sorted(fresh_dir.glob("*.png")):
        committed = committed_dir / fresh.name
        if not committed.exists() or not committed.with_suffix(".pdf").exists():
            problems.append(f"{fresh.stem}: missing")
            continue
        new = np.asarray(Image.open(fresh).convert("RGB"), dtype=np.int16)
        old = np.asarray(Image.open(committed).convert("RGB"), dtype=np.int16)
        if new.shape != old.shape:
            problems.append(f"{fresh.name}: {old.shape[:2]} on disk, {new.shape[:2]} fresh")
            continue
        largest = int(np.abs(new - old).max())
        if largest > PIXEL_TOLERANCE:
            problems.append(f"{fresh.name}: pixels differ by up to {largest}/255")
    return problems


# --- Figure 2: Demo 1, does demographic structure buy forecast skill? --------------

FLU_MODEL = "multi-strata-empirical"
"""The model panel (c) fits. Panels (b) and (d) show all three.

Which *places* the figures draw is not here: `demo-flu/evaluation.FOCUS_STATE` and
`REFERENCE_STATES` hold that, and the notebook reads the same two, so iterating on them
moves the paper and the notebook together. Demo 2's equivalent is `focus_counties`.
"""


def figure_2_flu(ev, replicate):
    """Figure 2: four panels in three rows, the same four Figure 3 has.

    Panel (d) is the headline. Panel (b) is pooled log WIS, which weights jurisdictions far
    more evenly than natural-scale WIS (where the four largest states dominate), but it is
    still one pooled number; the distribution over jurisdictions is the stronger statistic
    and the more honest one, and it is the only panel that draws both seeds.
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


# --- Supplementary: calibration ------------------------------------------------------


def figure_s_calibration(flu_ev, nominal: float = 0.95):
    """Interval coverage against nominal: panel (a) of the supplement's calibration figure.

    One file per demo since restructure step 5: the supplement places this beside Demo 2's
    (`figS-calibration-covid`, from `demo-covid.ipynb`) at the widths the two used to share
    one figure, a third and two thirds of the page, with the legend inside the panel.
    """
    fig = plt.figure(figsize=(DOUBLE_COLUMN / 3, 2.9), layout="constrained")
    flu.figure_calibration(flu_ev, nominal=nominal, subfig=fig, legend="axes")
    label_panels([fig], labels=["a"])
    return fig


def figure_s_flu_forecasts(ev):
    """Supplementary: Demo 1's rolling forecasts at both resolutions.

    (a) the six age bands the model actually forecasts, for one state; (b) the state
    totals those bands are summed into, which is what every score is computed on. Reading
    down is the aggregation the demo performs: summed **inside each realization**, before
    any quantile is taken, because quantiles do not add.

    `evaluation.FOCUS_STATE` leads `REFERENCE_STATES`, so it appears in both rows and one
    state can be traced from its bands to its total. The upper row is drawn in
    `manuscript_analysis.plots.FINE_SCALE`, a darker shade of the same blue, so two resolutions of
    one model do not read as two models.

    The fans over-predict during the growth phase, in both demos and at both resolutions.
    That is a real limitation of these models rather than a drawing artifact, and it is
    why this figure is supplementary and stated in the text rather than shown as a
    main-text result: the paper's claim is comparative, and every main-text panel is.
    """
    fig = plt.figure(figsize=(DOUBLE_COLUMN, 5.8), layout="constrained")
    channels, aggregate = fig.subfigures(2, 1, height_ratios=[3.4, 2.2])

    # The darker shade marks the model's own resolution, so the two rows cannot be read
    # as two models. See `manuscript_analysis.plots.FINE_SCALE`.
    flu.figure_rolling_forecasts_by_age(
        ev, flu.FOCUS_STATE, FLU_MODEL, title=None, subfig=channels, color=FINE_SCALE,
    )
    flu.figure_rolling_forecasts(
        ev, flu.focus_states(ev), FLU_MODEL, title=None, subfig=aggregate
    )
    label_panels([channels, aggregate])
    return fig


# --- Driver -----------------------------------------------------------------------

FIGURES = (
    "figure-2",
    "figure-s-calibration",
    "figure-s-flu-forecasts",
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
    parser.add_argument(
        "--check", action="store_true",
        help="build into a temporary folder and compare with what is on disk; write nothing",
    )
    args = parser.parse_args(argv)
    wanted = set(args.only or FIGURES)
    committed_dir = args.figures_dir
    if args.check:
        args.figures_dir = Path(tempfile.mkdtemp(prefix="figures-check-"))

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

    if "figure-s-calibration" in wanted:
        fig = figure_s_calibration(flu_ev)
        written += save_figure(fig, "figS-calibration-flu", args.figures_dir)
        plt.close(fig)

    if args.check:
        problems = drifted_figures(args.figures_dir, committed_dir)
        shutil.rmtree(args.figures_dir)
        if problems:
            raise SystemExit(
                f"{len(problems)} figure(s) have drifted:\n"
                + "".join(f"  {problem}\n" for problem in problems)
                + "Rebuild with scripts/build-figures.sh; never hand-edit them."
            )
        print(f"all {len(written) // 2} figures agree with a fresh build, "
              f"pixel for pixel within {PIXEL_TOLERANCE}/255")
        return

    for path in written:
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
