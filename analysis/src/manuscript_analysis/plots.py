"""Plotting for the manuscript's figures: the style, saving, and one function per panel.

The helpers take plain numpy and pandas objects and know nothing about epymorph or about
either demo: a demo notebook decides what goes in each panel and how the panels are laid
out, and these draw them. Both demos draw the same kinds of panel with the same
functions, so they differ in what a panel means, never in how it is drawn.

Sizes are Nature Methods' column widths, in inches. Figures are saved as PDF and PNG with
no timestamps or version strings, so their bytes change only when their drawing does.

Collected here from `demos/lib/figures.py` and `demos/lib/plots/` in restructure step 5.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from string import ascii_lowercase

import matplotlib as mpl
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.figure import Figure
from matplotlib.ticker import FixedLocator, NullLocator

# --- style, titles, panel letters and saving --------------------------------------


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
    figure_dir: Path,
    formats: tuple[str, ...] = ("pdf", "png"),
) -> list[Path]:
    """Save a figure as PDF (for typesetting) and PNG (for looking at) in `figure_dir`.

    Parameters
    ----------
    name :
        Base filename without extension, e.g. ``"fig2_flu_model_comparison"``.

    Returns
    -------
    :
        The paths written.
    """
    directory = Path(figure_dir)
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


# --- grids of panels --------------------------------------------------------------


def panel_grid(nrows: int, ncols: int, *, subfig=None, figsize=None, **kwargs):
    """Axes for one panel function, either standalone or inside a composed figure.

    Every `figure_*` in both demos takes an optional `subfig`. Passing none makes a
    standalone figure, which is what you want while choosing which states or counties to
    show. Passing a `SubFigure` draws into it instead, which is how a multi-panel
    manuscript figure gets assembled in code rather than in a slide editor.

    Returns
    -------
    :
        The figure (or subfigure) and its axes as a 2-D array, so callers can index
        `axs[row, column]` without worrying about matplotlib squeezing a single row.
    """
    fig = plt.figure(figsize=figsize, layout="constrained") if subfig is None else subfig
    return fig, np.atleast_2d(fig.subplots(nrows, ncols, **kwargs))


def as_panel_rows(
    panels: Sequence, ncols: int | None = None
) -> list[list[Mapping | None]]:
    """Normalize a panel argument to a rectangular list of rows.

    A flat sequence of panels is wrapped into rows `ncols` wide, padding the last row
    with `None` so the grid stays rectangular; `None` cells are drawn as blank space.
    A sequence of sequences is taken as the rows themselves, which is what a figure
    whose rows and columns both mean something (Demo 2's quantity by node) passes.
    """
    items = list(panels)
    if not items:
        raise ValueError("no panels to draw")

    is_flat = all(item is None or isinstance(item, Mapping) for item in items)
    if not is_flat:
        rows = [list(row) for row in items]
        widths = {len(row) for row in rows}
        if len(widths) != 1:
            raise ValueError(f"rows have different lengths: {sorted(widths)}")
        return rows

    width = len(items) if ncols is None else ncols
    rows = []
    for start in range(0, len(items), width):
        row = items[start:start + width]
        row = row + [None] * (width - len(row))
        rows.append(row)
    return rows


def _lowest_drawn(rows: Sequence[Sequence[Mapping | None]], column: int) -> int | None:
    """The bottom-most row index in `column` that holds a panel."""
    for row in range(len(rows) - 1, -1, -1):
        if rows[row][column] is not None:
            return row
    return None


def finish_panel_grid(
    fig,
    axs: np.ndarray,
    rows: Sequence[Sequence[Mapping | None]],
    *,
    ylabels: str | Sequence[str] | None = None,
    xlabel: str | None = None,
    title: str | None = None,
    legend_from=None,
    legend_order: Sequence[str] = (),
    label_rotation: float = 60,
    title_fontsize: float | None = None,
) -> None:
    """Apply the shared finishing to a grid whose panels have already been drawn.

    Parameters
    ----------
    rows :
        The panel specs the grid was drawn from, in the same shape as `axs`. Only the
        `"title"` key is read here; the rest is the drawing function's business.
    ylabels :
        One label for the whole figure, or one per row. Drawn on the first column.
    legend_from :
        The axes to take legend handles from, or None to draw no legend. Duplicate
        labels are dropped, so passing any drawn panel gives one entry per encoding.
    legend_order :
        Labels to put first, in this order; anything else follows in the order it was
        drawn. Matplotlib orders handles by artist type, so without this the same
        encoding drawn as bars and as bands legends itself in two different orders.
    """
    nrows, ncols = len(rows), len(rows[0])

    for row in range(nrows):
        for column in range(ncols):
            ax = axs[row, column]
            panel = rows[row][column]
            if panel is None:
                ax.set_visible(False)
                continue
            if panel.get("title") is not None:
                ax.set_title(panel["title"], fontsize=title_fontsize)
            ax.tick_params(axis="x", labelrotation=label_rotation)

    # The bottom of each column carries the dates, whatever row that turns out to be.
    for column in range(ncols):
        bottom = _lowest_drawn(rows, column)
        if bottom is None:
            continue
        ax = axs[bottom, column]
        ax.tick_params(axis="x", labelbottom=True, labelrotation=label_rotation)
        if xlabel is not None:
            ax.set_xlabel(xlabel)

    if ylabels is not None:
        per_row = [ylabels] * nrows if isinstance(ylabels, str) else list(ylabels)
        if len(per_row) != nrows:
            raise ValueError(f"expected {nrows} y labels, got {len(per_row)}")
        for row, label in enumerate(per_row):
            if label is not None and rows[row][0] is not None:
                axs[row, 0].set_ylabel(label)

    if legend_from is not None:
        handles, labels = legend_from.get_legend_handles_labels()
        unique = dict(zip(labels, handles))
        for label in reversed([x for x in legend_order if x in unique]):
            unique = {label: unique.pop(label), **unique}
        if unique:
            fig.legend(
                list(unique.values()), list(unique),
                loc="outside lower center", ncol=len(unique),
                fontsize=6, frameon=False,
            )

    if title is not None:
        fig.suptitle(title)


# --- time series ------------------------------------------------------------------


def _level(quantiles: Mapping[float, np.ndarray], value: float) -> np.ndarray:
    """Look up one quantile level, tolerating float representation."""
    matches = [q for q in quantiles if np.isclose(q, value)]
    if not matches:
        raise KeyError(f"quantile level {value} not available; have {sorted(quantiles)}")
    return np.asarray(quantiles[matches[0]], dtype=np.float64)


def plot_quantile_bands(
    ax: Axes,
    dates: Sequence,
    quantiles: Mapping[float, np.ndarray],
    color: str = "tab:blue",
    label: str | None = None,
    intervals: Sequence[float] = (0.95, 0.50),
    alphas: Sequence[float] = (0.25, 0.45),
    median_level: float = 0.5,
) -> None:
    """Draw nested central prediction intervals with a median line.

    Parameters
    ----------
    dates :
        The x values, one per time point.
    quantiles :
        Maps a quantile level to an array of values over ``dates``. Must
        contain the median and both endpoints of every requested interval.
    intervals :
        Nominal coverages to shade, widest first.
    alphas :
        Fill opacity for each interval, same length as ``intervals``.
    label :
        Legend label for the median line. The bands are labelled
        automatically as e.g. "95% PI".
    """
    if len(intervals) != len(alphas):
        raise ValueError("intervals and alphas must be the same length")

    def level(value: float) -> np.ndarray:
        return _level(quantiles, value)

    for nominal, alpha in zip(intervals, alphas):
        lower_level = (1.0 - nominal) / 2.0
        ax.fill_between(
            dates,
            level(lower_level),
            level(1.0 - lower_level),
            color=color,
            alpha=alpha,
            linewidth=0,
            label=f"{nominal:.0%} PI",
        )

    ax.plot(dates, level(median_level), color=color, label=label)


def plot_quantile_bars(
    ax: Axes,
    dates: Sequence,
    quantiles: Mapping[float, np.ndarray],
    color: str = "tab:blue",
    label: str | None = None,
    intervals: Sequence[float] = (0.95, 0.50),
    alphas: Sequence[float] = (0.25, 0.45),
    median_level: float = 0.5,
    width_fraction: float = 0.8,
) -> None:
    """Draw nested central prediction intervals as discrete bars.

    Same arguments as `plot_quantile_bands`, so the two are interchangeable, but
    the intervals are drawn as separate bars with a tick at the median instead of
    a connected ribbon.

    **Use this whenever consecutive values are separate predictions rather than one
    trajectory.** One-week-ahead forecasts are the clear case: each is issued from a
    freshly corrected state, so joining them into a ribbon implies a continuity
    between them that does not exist. The same applies to a filter's weekly
    posterior, where each week is its own assimilation.

    Parameters
    ----------
    width_fraction :
        Bar width as a fraction of the spacing between time points.
    """
    if len(intervals) != len(alphas):
        raise ValueError("intervals and alphas must be the same length")

    x = np.asarray(dates)
    if x.size < 2:
        raise ValueError("need at least two time points to size the bars")
    width = width_fraction * (x[1] - x[0])

    for nominal, alpha in zip(intervals, alphas):
        lower_level = (1.0 - nominal) / 2.0
        lower = _level(quantiles, lower_level)
        upper = _level(quantiles, 1.0 - lower_level)
        ax.bar(
            x=x,
            height=upper - lower,
            bottom=lower,
            width=width,
            color=color,
            alpha=alpha,
            linewidth=0,
            label=f"{nominal:.0%} PI",
        )

    # A short horizontal tick, not a connected line: see the note above. `hlines`
    # rather than `errorbar` because errorbar's xerr cannot take a date offset.
    half_width = width / 2
    ax.hlines(
        _level(quantiles, median_level),
        x - half_width,
        x + half_width,
        color=color,
        label=label,
    )


def plot_observations(
    ax: Axes,
    dates: Sequence,
    values: np.ndarray,
    label: str = "Observed",
    color: str = "black",
) -> None:
    """Overlay the observed series a forecast is being scored against."""
    ax.plot(
        dates,
        np.asarray(values, dtype=np.float64),
        color=color,
        linestyle="none",
        marker="o",
        markerfacecolor="none",
        markeredgewidth=0.7,
        label=label,
    )


def _observed_pair(observed, dates):
    """Split a panel's `observed` entry into x and y.

    A tuple is an explicit `(dates, values)` pair, for observations on their own dates;
    anything else is an array of values aligned to the panel's `dates`.
    """
    if isinstance(observed, tuple):
        return observed
    return dates, np.asarray(observed, dtype=np.float64)


def plot_quantile_grid(
    panels: Sequence,
    *,
    ncols: int | None = None,
    style: str = "bars",
    ylabels: str | Sequence[str] | None = None,
    xlabel: str | None = None,
    title: str | None = None,
    median_label: str = "Median",
    observed_label: str = "Observed",
    reference_label: str = "Reference",
    legend: bool | None = None,
    figure_width: float = 7.20,
    panel_height: float = 1.8,
    sharex: bool = True,
    sharey: bool = False,
    subfig=None,
) -> tuple[Figure, np.ndarray]:
    """A grid of quantile panels sharing one legend.

    The recurring fit figure in both demos: one panel per age band (Demo 1), per county
    or per quantity by node (Demo 2), each showing prediction intervals and optionally
    the observations they are compared against.

    Parameters
    ----------
    panels :
        Either a flat sequence of panel mappings, wrapped into rows `ncols` wide, or a
        sequence of rows when both axes of the grid mean something. A `None` in place of
        a panel leaves that cell blank. Each panel is a mapping with:

        - `dates`: the x values (required).
        - `quantiles`: level to array over `dates` (required).
        - `observed`: values aligned to `dates`, or an explicit `(dates, values)` pair.
        - `color`, `title`, and `reference` (a horizontal line, e.g. a prior anchor).
    style :
        ``"bars"`` for discrete weekly quantities, ``"bands"`` for a continuous process.
        See `plot_quantile_bars` for why the distinction matters.
    ylabels :
        One label for the figure, or one per row; drawn on the first column only.
    legend :
        Defaults to on for a standalone figure and off inside a `subfig`, where the
        composed figure carries one legend for everything.

    Returns
    -------
    :
        The figure (or subfigure) and its axes as a 2-D array.
    """
    if style not in ("bars", "bands"):
        raise ValueError(f"style must be 'bars' or 'bands', got {style!r}")
    draw = plot_quantile_bars if style == "bars" else plot_quantile_bands

    rows = as_panel_rows(panels, ncols)
    fig, axs = panel_grid(
        len(rows), len(rows[0]), subfig=subfig,
        figsize=(figure_width, panel_height * len(rows)),
        sharex=sharex, sharey=sharey,
    )

    drawn = None
    for row, cells in enumerate(rows):
        for column, panel in enumerate(cells):
            if panel is None:
                continue
            ax = axs[row, column]
            dates = panel["dates"]
            draw(
                ax, dates, panel["quantiles"],
                color=panel.get("color", "tab:blue"), label=median_label,
            )
            if panel.get("observed") is not None:
                seen_dates, seen_values = _observed_pair(panel["observed"], dates)
                plot_observations(ax, seen_dates, seen_values, label=observed_label)
            if panel.get("reference") is not None:
                ax.axhline(
                    panel["reference"], color="black", linestyle=":", linewidth=0.8,
                    label=reference_label,
                )
            if drawn is None:
                drawn = ax

    if legend is None:
        legend = subfig is None
    finish_panel_grid(
        fig, axs, rows,
        ylabels=ylabels, xlabel=xlabel, title=title,
        legend_from=drawn if legend else None,
        legend_order=(median_label, observed_label),
    )
    return fig, axs


def plot_rolling_forecasts(
    ax: Axes,
    origins: Sequence,
    horizons: Sequence[int],
    values: np.ndarray,
    levels: Sequence[float],
    color: str = "tab:blue",
    observed: tuple[Sequence, np.ndarray] | None = None,
    week_days: int = 7,
) -> None:
    """One panel of a rolling-origin figure: every origin's fan, plus what happened.

    Both demos draw this panel and they draw it identically, so it lives here rather
    than in either `evaluation.py`: Demo 1 has one panel per state and one per age band,
    Demo 2 one per state or county per quantity, and the only thing that differs between
    them is the grid the panels sit in.

    Bands rather than bars, unlike the filter fits: a single origin's horizons ARE one
    trajectory, so joining them is honest. See `plot_quantile_bars` for the other case.

    Parameters
    ----------
    origins :
        One reference date per forecast, anything `pd.Timestamp` accepts.
    horizons :
        Weeks ahead, so a target date is `origin + week_days * horizon`.
    values :
        Shape `(origins, horizons, levels)`, the quantiles of every forecast.
    levels :
        The quantile level of each entry along the last axis of `values`.
    observed :
        A `(dates, values)` pair for the series the forecasts are scored against, or
        None to draw the fans alone.
    week_days :
        Days per unit of horizon. Only change this for a non-weekly target.
    """
    values = np.asarray(values, dtype=np.float64)
    expected = (len(origins), len(horizons), len(levels))
    if values.shape != expected:
        raise ValueError(
            f"values must be (origins, horizons, levels) = {expected}, "
            f"got {values.shape}"
        )

    for o, origin in enumerate(origins):
        dates = [
            pd.Timestamp(origin) + pd.Timedelta(days=week_days * int(h))
            for h in horizons
        ]
        plot_quantile_bands(
            ax,
            dates,
            {level: values[o, :, i] for i, level in enumerate(levels)},
            color=color,
        )

    if observed is not None:
        observed_dates, observed_values = observed
        plot_observations(ax, observed_dates, observed_values)


def plot_rolling_forecast_grid(
    panels: Sequence,
    levels: Sequence[float],
    *,
    ncols: int | None = None,
    ylabels: str | Sequence[str] | None = None,
    xlabel: str | None = None,
    title: str | None = None,
    legend: bool = False,
    figure_width: float = 7.20,
    panel_height: float = 1.8,
    sharex: bool = True,
    sharey: bool = False,
    subfig=None,
    week_days: int = 7,
) -> tuple[Figure, np.ndarray]:
    """A grid of rolling-origin panels: every origin's fan, plus what happened.

    The companion to `plot_quantile_grid`, laid out by the same rules. Demo 1 draws one
    panel per state and one per age band, Demo 2 one per quantity by node, and the only
    thing that differs between them is what a row and a column mean.

    Parameters
    ----------
    panels :
        A flat sequence wrapped into rows `ncols` wide, or a sequence of rows; `None`
        leaves a cell blank. Each panel is a mapping with:

        - `origins`, `horizons`, `values`: as `plot_rolling_forecasts` takes them, with
          `values` of shape `(origins, horizons, levels)`.
        - `levels`: this panel's quantile levels, if they differ from the figure's.
        - `observed`: a `(dates, values)` pair for the series being forecast.
        - `color` and `title`.
    legend :
        Off by default. Every origin draws the same two bands, so the legend says only
        what the caption already does; turn it on for a panel read on its own.

    Returns
    -------
    :
        The figure (or subfigure) and its axes as a 2-D array.
    """
    rows = as_panel_rows(panels, ncols)
    fig, axs = panel_grid(
        len(rows), len(rows[0]), subfig=subfig,
        figsize=(figure_width, panel_height * len(rows)),
        sharex=sharex, sharey=sharey,
    )

    drawn = None
    for row, cells in enumerate(rows):
        for column, panel in enumerate(cells):
            if panel is None:
                continue
            ax = axs[row, column]
            plot_rolling_forecasts(
                ax,
                panel["origins"],
                panel["horizons"],
                panel["values"],
                panel.get("levels", levels),
                color=panel.get("color", "tab:blue"),
                observed=panel.get("observed"),
                week_days=week_days,
            )
            if drawn is None:
                drawn = ax

    finish_panel_grid(
        fig, axs, rows,
        ylabels=ylabels, xlabel=xlabel, title=title,
        legend_from=drawn if legend else None,
    )
    return fig, axs


def plot_line_panels(
    x: Sequence,
    series: Mapping[str, np.ndarray],
    titles: Sequence[str] | None = None,
    colors: Mapping[str, object] | None = None,
    ylabel: str | None = None,
    xlabel: str | None = None,
    suptitle: str | None = None,
    reference: float | None = None,
    reference_label: str = "Nominal",
    log_y: bool = False,
    marker: str | None = "o",
    xticks: Sequence | None = None,
    ylim: tuple[float, float] | None = None,
    legend: bool | str = True,
    legend_loc: str = "lower left",
    figure_width: float = 7.20,
    panel_height: float = 2.1,
    share_y: bool = True,
    subfig=None,
) -> tuple[Figure, np.ndarray]:
    """A row of line panels sharing one legend.

    Parameters
    ----------
    series :
        Maps a legend label to an array of shape ``(panels, len(x))``. Every
        entry must have the same number of panels.
    reference :
        Drawn as a dotted horizontal line in every panel. Use for a nominal
        coverage level, or 1.0 on a ratio scale.
    xticks :
        Tick positions, for an x axis of a few integers such as forecast horizons,
        where matplotlib's automatic ticks land between the values.
    ylim :
        Fixed y limits. Coverage wants `(0, 1)`, so a model that covers nothing and a
        model that covers everything are read off the same scale.
    legend :
        True for one legend under the whole figure, False for none, or ``"axes"`` to
        put it inside the first panel. Use ``"axes"`` when this figure is a subfigure
        sitting *beside* another one: two "outside" legends are both placed against the
        parent figure and land on top of each other.
    legend_loc :
        The corner an ``"axes"`` legend sits in. Pick the one the data leaves empty:
        coverage curves fall away from the top, skill curves rise away from the bottom.
    """
    shapes = {np.asarray(v).shape for v in series.values()}
    if len(shapes) != 1:
        raise ValueError(f"all series must have the same shape, got {shapes}")
    panels = next(iter(shapes))[0]

    fig, grid = panel_grid(
        1,
        panels,
        subfig=subfig,
        figsize=(figure_width, panel_height),
        sharex=True,
        sharey=share_y,
    )
    axs = grid[0]

    for panel, ax in enumerate(axs):
        for name, values in series.items():
            color = None if colors is None else colors.get(name)
            ax.plot(x, np.asarray(values)[panel], marker=marker,
                    markersize=2.5, color=color, label=name)
        if reference is not None:
            ax.axhline(reference, color="black", linestyle=":", linewidth=0.8,
                       label=reference_label)
        if log_y:
            ax.set_yscale("log")
        if xticks is not None:
            ax.set_xticks(list(xticks))
        if ylim is not None:
            ax.set_ylim(*ylim)
        if titles is not None:
            ax.set_title(titles[panel])
        if xlabel is not None:
            ax.set_xlabel(xlabel)

    if ylabel is not None:
        axs[0].set_ylabel(ylabel)

    if legend:
        handles, labels = axs[0].get_legend_handles_labels()
        unique = dict(zip(labels, handles))
        if legend == "axes":
            # An explicit corner, not matplotlib's default `loc="best"`: "best" asks the
            # renderer which position overlaps the data least, and the answer is not
            # stable across runs. It made this figure's PNG flip between two byte values
            # on alternate builds, which is poison for a repository whose premise is
            # regenerate-and-compare.
            axs[0].legend(list(unique.values()), list(unique), fontsize=6,
                          loc=legend_loc)
        else:
            fig.legend(list(unique.values()), list(unique), loc="outside lower center",
                       ncol=len(unique), fontsize=6, frameon=False)
    if suptitle is not None:
        fig.suptitle(suptitle)
    return fig, axs


def plot_single_forecast_grid(
    rows: Sequence[Sequence[Mapping | None]],
    *,
    colors: Mapping[str, object],
    ylabels: str | Sequence[str] | None = None,
    interval: float = 0.95,
    alpha: float = 0.25,
    title: str | None = None,
    subfig=None,
    figsize=None,
) -> tuple[Figure, np.ndarray]:
    """One forecast, issued from one origin, by one or more models, panel by panel.

    The teaching counterpart of `plot_rolling_forecast_grid`: a single origin rather
    than every origin, so a reader sees exactly what one call to the forecast simulator
    produced and what then happened.

    Parameters
    ----------
    rows :
        Panel specs, row by row. Each is a mapping with keys `dates` and `observed` (the
        whole observed series), `origin` (the first forecast date: observations before
        it are filled, the ones the filter saw; from it on they are hollow, held out),
        `forecast_dates`, `forecasts` (model label -> {quantile level: values over
        `forecast_dates`}) and optionally `title`.
    colors :
        Model label -> colour. The colour follows the model in every panel.
    interval :
        Nominal coverage of the band drawn for each model, around its median line.
    """
    rows = as_panel_rows(rows)
    nrows, ncols = len(rows), len(rows[0])
    if figsize is None:
        figsize = (2.4 * ncols, 1.9 * nrows + 0.5)
    fig, axs = panel_grid(nrows, ncols, subfig=subfig, figsize=figsize, sharex=True)

    lower_level = (1.0 - interval) / 2.0
    for row in range(nrows):
        for column in range(ncols):
            panel = rows[row][column]
            if panel is None:
                continue
            ax = axs[row, column]
            dates = pd.to_datetime(np.asarray(panel["dates"]))
            observed = np.asarray(panel["observed"], dtype=np.float64)
            seen = dates < pd.Timestamp(panel["origin"])

            ax.plot(dates[seen], observed[seen], color="black", linestyle="none",
                    marker="o", markersize=2.5, label="observed, assimilated")
            ax.plot(dates[~seen], observed[~seen], color="black", linestyle="none",
                    marker="o", markersize=2.5, markerfacecolor="none",
                    markeredgewidth=0.7, label="observed, held out")
            ax.axvline(pd.Timestamp(panel["origin"]), color="0.6", linewidth=0.6,
                       linestyle=":", zorder=0)

            forecast_dates = pd.to_datetime(np.asarray(panel["forecast_dates"]))
            for label, quantiles in panel["forecasts"].items():
                ax.fill_between(
                    forecast_dates,
                    _level(quantiles, lower_level),
                    _level(quantiles, 1.0 - lower_level),
                    color=colors[label], alpha=alpha, linewidth=0,
                )
                ax.plot(forecast_dates, _level(quantiles, 0.5), color=colors[label],
                        linewidth=1.2, label=f"{label}: median, {interval:.0%} PI")
            ax.set_ylim(bottom=0)

    finish_panel_grid(
        fig, axs, rows, ylabels=ylabels, title=title, legend_from=axs[0, 0],
        label_rotation=45,
    )
    return fig, axs


# --- matrices ---------------------------------------------------------------------


def plot_contact_matrix(
    ax: Axes,
    matrix: np.ndarray,
    labels: list[str],
    title: str | None = None,
    cmap=SEQUENTIAL,
    norm: Normalize | None = None,
    annotate: bool = True,
    value_format: str = "{:.2f}",
):
    """Draw a contact matrix as an annotated heatmap.

    Rows are the contactor, columns the contactee, matching the matrix
    convention throughout `manuscript_analysis.demos.lib.contacts`.

    Parameters
    ----------
    norm :
        Share one `Normalize` across panels so they are comparable. Panels drawn
        on independent scales invite exactly the wrong comparison.
    annotate :
        Print the value in each cell. Worth it at this size: a 6x6 matrix has few
        enough cells that direct labels beat reading values off a colorbar.

    Returns
    -------
    :
        The image, for attaching a colorbar.
    """
    image = ax.imshow(matrix, cmap=cmap, norm=norm, aspect="equal")

    ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("contact with (age)")
    ax.set_ylabel("age of individual")
    if title is not None:
        ax.set_title(title)

    # Hairline separators so adjacent cells read as distinct marks.
    ax.set_xticks(np.arange(len(labels) + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(labels) + 1) - 0.5, minor=True)
    ax.grid(which="minor", color="white", linewidth=1.0)
    ax.tick_params(which="minor", length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    if annotate:
        # Text wears an ink color, not the series color: pick whichever of
        # near-black / white actually reads against the cell behind it.
        rgba = image.cmap(image.norm(matrix))
        luminance = rgba[..., :3] @ np.array([0.2126, 0.7152, 0.0722])
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                ax.text(
                    j,
                    i,
                    value_format.format(matrix[i, j]),
                    ha="center",
                    va="center",
                    fontsize=5,
                    color="#0b0b0b" if luminance[i, j] > 0.55 else "#ffffff",
                )

    return image


def plot_flow_matrix(
    ax: Axes,
    matrix: np.ndarray,
    groups: np.ndarray,
    group_labels: list[str] | None = None,
    log: bool = True,
    cmap=SEQUENTIAL,
    xlabel: str = "destination",
    ylabel: str = "origin",
):
    """Draw an origin-destination flow matrix, with group blocks marked.

    The companion to `plot_contact_matrix` for matrices too large to annotate cell by
    cell. Rows are the origin, columns the destination.

    Parameters
    ----------
    groups :
        One label per row, in row order, used to draw block boundaries. Rows must already
        be sorted by group, which is what a FIPS-ordered scope gives you; a group that is
        not contiguous would draw misleading boundaries, so this is checked.
    log :
        Plot `log10(matrix + 1)`. On by default because the diagonal of a commuting
        matrix runs two to three orders of magnitude above the off-diagonal, and on a
        linear scale the off-diagonal structure, which is the whole point, is invisible.

    Returns
    -------
    :
        The image, for attaching a colorbar.
    """
    groups = np.asarray(groups)
    if matrix.shape[0] != matrix.shape[1] or matrix.shape[0] != groups.size:
        raise ValueError(
            f"matrix is {matrix.shape} but there are {groups.size} group labels"
        )
    for group in np.unique(groups):
        positions = np.where(groups == group)[0]
        if positions.size != positions[-1] - positions[0] + 1:
            raise ValueError(f"group {group!r} is not contiguous; sort the rows first")

    shown = np.log10(matrix + 1) if log else matrix
    image = ax.imshow(shown, cmap=cmap, interpolation="nearest")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    # Separate the blocks so the within-group structure is visible, and label each at its
    # centre on the diagonal, where it cannot be confused for a data point.
    boundaries = np.where(groups[:-1] != groups[1:])[0] + 0.5
    for boundary in boundaries:
        ax.axhline(boundary, color="white", linewidth=0.6)
        ax.axvline(boundary, color="white", linewidth=0.6)

    if group_labels is not None:
        for group, label in zip(np.unique(groups), group_labels):
            centre = float(np.where(groups == group)[0].mean())
            ax.text(
                centre, centre, label, ha="center", va="center", fontsize=7,
                color="white", fontweight="bold",
                path_effects=[pe.withStroke(linewidth=1.6, foreground="black")],
            )
    return image


# --- distributions ----------------------------------------------------------------


def swarm_offsets(
    values: np.ndarray, width: float = 0.30, bins: int = 24
) -> np.ndarray:
    """Vertical offsets that spread overlapping points into a symmetric swarm.

    Deterministic, unlike jitter: the same data always draws the same figure, which
    matters because these are manuscript figures regenerated on every build.
    """
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return values
    low, high = np.log(values.min()), np.log(values.max()) + 1e-9
    edges = np.linspace(low, high, bins + 1)
    which = np.clip(np.digitize(np.log(values), edges) - 1, 0, bins - 1)
    offsets = np.zeros(values.size)
    for b in range(bins):
        members = np.where(which == b)[0]
        if members.size == 0:
            continue
        members = members[np.argsort(values[members])]
        count = members.size
        spread = min(width, 0.055 * count)
        offsets[members] = (
            (np.arange(count) - (count - 1) / 2) / max(count - 1, 1) * spread
        )
    return offsets


def plot_ratio_swarm(
    ax: Axes,
    rows: Sequence[Mapping],
    *,
    ticks: Sequence[float] = (0.5, 0.7, 1.0, 1.5, 2.0, 3.0),
    reference: float = 1.0,
    point_size: float = 5.5,
    annotate_counts: bool = True,
) -> list[str]:
    """One row per contrast; one mark per unit, or one mark per unit per replicate.

    Each row is a mapping with `label`, `color`, and `seeds`: a sequence of arrays, one
    per replicate, each holding the ratio for every unit in the same order.

    **With more than one replicate, every replicate is drawn**, joined by a line, rather
    than a point and a range. A point with a whisker is the idiom for a mean with a
    confidence interval over many samples; using it for two replicates makes the analysis
    look better powered than it is. Median ticks are offset onto opposite halves of the
    row for the same reason: two nearly equal medians would otherwise draw as one line.

    Returns
    -------
    :
        The y tick labels, so the caller can decide how to place them.
    """
    labels = []
    for index, row in enumerate(rows):
        seeds = [np.asarray(s, dtype=float) for s in row["seeds"]]
        if len({s.size for s in seeds}) != 1:
            raise ValueError(f"row {row['label']!r} has replicates of different lengths")
        colour = row["color"]
        base = len(rows) - 1 - index
        # Position by the geometric mean so a unit sits in one place regardless of which
        # replicate is being drawn.
        centre = np.exp(np.mean([np.log(s) for s in seeds], axis=0))
        y = base + swarm_offsets(centre)

        if len(seeds) > 1:
            ax.hlines(y, np.min(seeds, axis=0), np.max(seeds, axis=0),
                      color=colour, linewidth=0.6, alpha=0.5, zorder=1)
        ax.scatter(np.concatenate(seeds), np.tile(y, len(seeds)),
                   s=point_size, color=colour, zorder=3, linewidth=0)

        for position, ratios in enumerate(seeds):
            low = base + (0.02 if position == 0 else -0.46)
            ax.vlines(np.median(ratios), low, low + 0.44,
                      color=colour, linewidth=1.2, zorder=4)
        ax.text(float(np.median(centre)), base + 0.47,
                " / ".join(f"{np.median(s):.2f}" for s in seeds),
                color=colour, fontsize=6, ha="center", va="bottom")

        label = row["label"]
        if annotate_counts:
            wins = " / ".join(str(int((s < reference).sum())) for s in seeds)
            label = f"{label}\nbetter in {wins} of {seeds[0].size}"
        labels.append(label)

    ax.axvline(reference, color="black", linewidth=0.9, zorder=2)
    # A ratio belongs on a log axis: halving and doubling are equally far from 1.
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(FixedLocator(list(ticks)))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xticklabels([f"{t:g}" for t in ticks])
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(list(reversed(labels)), fontsize=6)
    ax.tick_params(axis="y", length=0)
    ax.set_ylim(-0.75, len(rows) - 0.25)
    for side in ("left", "right", "top"):
        ax.spines[side].set_visible(False)
    return labels
