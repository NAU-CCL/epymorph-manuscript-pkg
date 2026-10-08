"""Manuscript figure styling and export.

Target journal is Nature Methods, so figures are sized to its column widths and
saved as vector PDF (for typesetting) alongside PNG (for quick viewing).
"""

from collections.abc import Sequence
from pathlib import Path
from string import ascii_lowercase

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from manuscript_analysis.demos import paths

FIGURE_DIR = paths.FIGURES

# Nature Methods column widths, in inches.
SINGLE_COLUMN = 3.50
ONE_AND_HALF_COLUMN = 4.75
DOUBLE_COLUMN = 7.20

FINE_SCALE = "#104281"
"""A darker shade of the added-structure blue, for a panel drawn at the model's **own**
resolution beside one drawn at the scale the models are scored at.

A shade rather than a new hue, deliberately. The model is the same and only the
resolution differs, so a new hue would read as a fourth model; and the three hues of each
demo's `COLORS` are already spoken for by the three models.

Used only where both resolutions appear in one figure, which is where the contrast means
something: the supplementary forecast figures, whose upper row is the model's own age
bands or counties and whose lower row is the scored states. A panel drawn at one
resolution alone keeps its model's colour, since there would be nothing to contrast with.
Taken from `SEQUENTIAL`, so it is the same blue family the matrices use."""

AUTO_TITLE = "auto"
"""The default `title` argument: draw the figure's own built-in title.

See `resolve_title`. Spelled as a word rather than a sentinel object so a call
reads plainly and so a notebook can pass it without importing anything."""

MANUSCRIPT_STYLE = {
    "figure.dpi": 150,
    "savefig.dpi": 600,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 7,
    "axes.labelsize": 7,
    "axes.titlesize": 7,
    "axes.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.labelsize": 6,
    "ytick.labelsize": 6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "legend.fontsize": 6,
    "legend.frameon": False,
    "lines.linewidth": 1.0,
    "lines.markersize": 3.0,
    # Keep text as text in the PDF so the typesetter can edit it.
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}


def use_manuscript_style() -> None:
    """Apply the manuscript rcParams to the current session."""
    mpl.rcParams.update(MANUSCRIPT_STYLE)


def resolve_title(title: str | None, default: str) -> str | None:
    """Work out what a figure's title should be, given what the caller asked for.

    Every `figure_*` function in both demos takes `title`, so a title can be reworded or
    dropped at the call site rather than edited in the function that draws the figure.
    The convention, one place so it is the same everywhere:

    - `"auto"`, the default, gives the figure's own title, which is usually built from
      the model and location being drawn.
    - `None` gives no title. This is what a panel of a composed multi-panel figure
      wants, where the caption carries what the title would have said.
    - Any other string is used as given.
    """
    return default if title == AUTO_TITLE else title


def label_panels(
    subfigs: Sequence,
    labels: Sequence[str] | None = None,
    x: float = 0.0,
    y: float = 0.99,
    fontsize: float = 8.0,
) -> None:
    """Stamp (a), (b), (c) on the subfigures of a composed multi-panel figure.

    One function so Figures 2 and 3 are labelled identically. The label goes on the
    *subfigure*, not on an axes, so it sits at the top left of the whole panel rather
    than of the panel's first plot, which is what a reader looks for.

    Parameters
    ----------
    subfigs :
        The subfigures, in reading order: left to right, then top to bottom.
    labels :
        Override the default a, b, c, ... for a figure that continues another's
        lettering or skips one.
    """
    if labels is None:
        labels = ascii_lowercase[:len(subfigs)]
    if len(labels) != len(subfigs):
        raise ValueError(f"{len(subfigs)} subfigures but {len(labels)} labels")
    for subfig, label in zip(subfigs, labels):
        subfig.text(
            x, y, f"({label})",
            fontsize=fontsize, fontweight="bold", va="top", ha="left",
        )


def save_figure(
    fig: plt.Figure,
    name: str,
    figure_dir: Path | None = None,
    formats: tuple[str, ...] = ("pdf", "png"),
) -> list[Path]:
    """Save a figure to the project's ``figures/`` directory.

    Parameters
    ----------
    name :
        Base filename without extension, e.g. ``"fig2_flu_model_comparison"``.

    Returns
    -------
    :
        The paths written.
    """
    directory = FIGURE_DIR if figure_dir is None else figure_dir
    directory.mkdir(parents=True, exist_ok=True)

    paths = []
    for extension in formats:
        path = directory / f"{name}.{extension}"
        fig.savefig(path, metadata=_REPRODUCIBLE_METADATA.get(extension))
        paths.append(path)
    return paths


_REPRODUCIBLE_METADATA = {
    "pdf": {"CreationDate": None, "Creator": None, "Producer": None},
    "png": {"Software": None},
}
"""No timestamps or version strings, so a figure's bytes change only when its drawing does
and the files can be checksummed. By default a PDF records when it was made, and both
formats record the matplotlib version."""


# --- Colormaps -----------------------------------------------------------------
#
# Two jobs, two rules (see the `dataviz` guidance):
#
# - **Magnitude** (a contact matrix, a rate) takes a *sequential* map: one hue,
#   light to dark. Never a rainbow.
# - **Polarity** (a ratio around 1, a difference around 0) takes a *diverging*
#   map: two hues with a neutral gray midpoint, so "no change" reads as nothing.

_SEQUENTIAL_BLUE = [
    "#cde2fb",
    "#b7d3f6",
    "#9ec5f4",
    "#86b6ef",
    "#6da7ec",
    "#5598e7",
    "#3987e5",
    "#2a78d6",
    "#256abf",
    "#1c5cab",
    "#184f95",
    "#104281",
    "#0d366b",
]

SEQUENTIAL = LinearSegmentedColormap.from_list("epy_sequential", _SEQUENTIAL_BLUE)
"""Single-hue light-to-dark ramp, for continuous magnitude."""

