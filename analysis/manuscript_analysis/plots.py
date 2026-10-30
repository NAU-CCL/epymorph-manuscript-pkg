"""Plotting for the manuscript's figures: the style, saving, and one function per panel.

The helpers take plain numpy and pandas objects and know nothing about epymorph or about
either demo: a demo notebook decides what goes in each panel and how the panels are laid
out, and these draw them. Both demos draw the same kinds of panel with the same
functions, so they differ in what a panel means, never in how it is drawn.

Sizes are Nature Methods' column widths, in inches. Figures are saved as PDF and PNG with
no timestamps or version strings, so their bytes change only when their drawing does.
`ADDING-FIGURES.md`, beside this file, says how a new figure fits in.
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
from matplotlib.ticker import FixedLocator, NullLocator

# --- style, panel letters and saving ----------------------------------------------

# Nature Methods column widths, in inches.
SINGLE_COLUMN = 3.50
ONE_AND_HALF_COLUMN = 4.75
DOUBLE_COLUMN = 7.20

FINE_SCALE = "#104281"
"""A darker shade of the models' blue, for a panel drawn at the model's own resolution
(age groups, counties) beside one drawn at the scored states: a shade, not a new hue, so
two resolutions of one model do not read as two models."""

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


def label_panels(subfigs: Sequence, labels: Sequence[str] | None = None) -> None:
    """Stamp (a), (b), (c) at the top left of each subfigure, given in reading order.

    `labels` overrides the default a, b, c, for a figure that continues another's
    lettering.
    """
    if labels is None:
        labels = ascii_lowercase[:len(subfigs)]
    if len(labels) != len(subfigs):
        raise ValueError(f"{len(subfigs)} subfigures but {len(labels)} labels")
    for subfig, label in zip(subfigs, labels):
        subfig.text(0.0, 0.99, f"({label})", fontsize=8.0, fontweight="bold",
                    va="top", ha="left")


# No timestamps or version strings, so a figure's bytes change only when its drawing does.
_REPRODUCIBLE_METADATA = {
    "pdf": {"CreationDate": None, "Creator": None, "Producer": None},
    "png": {"Software": None},
}


def save_figure(fig, name: str, figure_dir: Path) -> None:
    """Save `fig` as `<name>.pdf` (for typesetting) and `<name>.png` in `figure_dir`."""
    directory = Path(figure_dir)
    directory.mkdir(parents=True, exist_ok=True)
    for extension in ("pdf", "png"):
        fig.savefig(directory / f"{name}.{extension}",
                    metadata=_REPRODUCIBLE_METADATA[extension])


# A single-hue light-to-dark ramp, for magnitude (a contact rate, a commuting flow).
SEQUENTIAL = LinearSegmentedColormap.from_list("epy_sequential", [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
    "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b",
])


# --- grids of panels --------------------------------------------------------------


def panel_grid(nrows: int, ncols: int, *, subfig=None, figsize=None, **kwargs):
    """A figure (or the given subfigure) and its axes, always as a 2-D array.

    With no `subfig`, a standalone figure; with one, the axes are drawn inside it, which
    is how a multi-panel figure is assembled in code.
    """
    fig = plt.figure(figsize=figsize, layout="constrained") if subfig is None else subfig
    return fig, np.atleast_2d(fig.subplots(nrows, ncols, **kwargs))


def _as_rows(panels: Sequence, ncols: int | None = None) -> list[list[Mapping | None]]:
    """A flat list of panels wrapped into rows `ncols` wide (the last padded with None),
    or a list of rows as given, when both axes of the grid mean something."""
    items = list(panels)
    if not items:
        raise ValueError("no panels to draw")
    if not all(item is None or isinstance(item, Mapping) for item in items):
        return [list(row) for row in items]

    width = len(items) if ncols is None else ncols
    rows = []
    for start in range(0, len(items), width):
        row = items[start:start + width]
        rows.append(row + [None] * (width - len(row)))
    return rows


def _finish_grid(fig, axs, rows, *, ylabels=None, title=None, legend_from=None,
                 label_rotation=60) -> None:
    """The finishing every grid shares: panel titles, dates on the bottom panel of each
    column, y labels on the first column (one for all rows, or one per row), an optional
    legend below the figure, and an optional title."""
    nrows, ncols = len(rows), len(rows[0])
    for row in range(nrows):
        for column in range(ncols):
            ax, panel = axs[row, column], rows[row][column]
            if panel is None:
                ax.set_visible(False)
                continue
            if panel.get("title") is not None:
                ax.set_title(panel["title"])
            ax.tick_params(axis="x", labelrotation=label_rotation)

    for column in range(ncols):
        drawn = [row for row in range(nrows) if rows[row][column] is not None]
        if drawn:
            axs[drawn[-1], column].tick_params(
                axis="x", labelbottom=True, labelrotation=label_rotation
            )

    if ylabels is not None:
        per_row = [ylabels] * nrows if isinstance(ylabels, str) else list(ylabels)
        for row, label in enumerate(per_row):
            if label is not None and rows[row][0] is not None:
                axs[row, 0].set_ylabel(label)

    if legend_from is not None:
        handles, labels = legend_from.get_legend_handles_labels()
        unique = dict(zip(labels, handles))
        fig.legend(list(unique.values()), list(unique), loc="outside lower center",
                   ncol=len(unique), fontsize=6, frameon=False)

    if title is not None:
        fig.suptitle(title)


# --- time series ------------------------------------------------------------------

# The central intervals every quantile panel shades, widest first, with their opacity.
INTERVALS = ((0.95, 0.25), (0.50, 0.45))


def _level(quantiles: Mapping[float, np.ndarray], value: float) -> np.ndarray:
    """One quantile level's values, tolerating float representation."""
    matches = [q for q in quantiles if np.isclose(q, value)]
    if not matches:
        raise KeyError(f"quantile level {value} not available; have {sorted(quantiles)}")
    return np.asarray(quantiles[matches[0]], dtype=np.float64)


def _quantile_bands(ax: Axes, dates, quantiles, color) -> None:
    """Nested central intervals as a ribbon, with a median line: for one trajectory."""
    for nominal, alpha in INTERVALS:
        lower = (1.0 - nominal) / 2.0
        ax.fill_between(dates, _level(quantiles, lower), _level(quantiles, 1.0 - lower),
                        color=color, alpha=alpha, linewidth=0, label=f"{nominal:.0%} PI")
    ax.plot(dates, _level(quantiles, 0.5), color=color)


def _quantile_bars(ax: Axes, dates, quantiles, color, label) -> None:
    """Nested central intervals as separate bars, with a tick at the median.

    For values that are separate predictions rather than one trajectory, such as a
    filter's one-week-ahead fit, each issued from a freshly corrected state: a ribbon
    would imply a continuity between them that does not exist.
    """
    x = np.asarray(dates)
    width = 0.8 * (x[1] - x[0])
    for nominal, alpha in INTERVALS:
        lower = _level(quantiles, (1.0 - nominal) / 2.0)
        upper = _level(quantiles, 1.0 - (1.0 - nominal) / 2.0)
        ax.bar(x=x, height=upper - lower, bottom=lower, width=width, color=color,
               alpha=alpha, linewidth=0, label=f"{nominal:.0%} PI")
    # `hlines` rather than `errorbar`, whose xerr cannot take a date offset.
    ax.hlines(_level(quantiles, 0.5), x - width / 2, x + width / 2, color=color,
              label=label)


def _observations(ax: Axes, dates, values) -> None:
    """The observed series, as hollow points."""
    ax.plot(dates, np.asarray(values, dtype=np.float64), color="black", linestyle="none",
            marker="o", markerfacecolor="none", markeredgewidth=0.7, label="Observed")


def plot_quantile_grid(
    panels: Sequence,
    *,
    ncols: int | None = None,
    ylabels: str | Sequence[str] | None = None,
    figure_width: float = DOUBLE_COLUMN,
    panel_height: float = 1.8,
    subfig=None,
):
    """A grid of weekly fits: each panel's intervals as bars, and what was observed.

    `panels` is a flat list wrapped into rows `ncols` wide, or a list of rows; `None`
    leaves a cell blank. Each panel has `dates`, `quantiles` (level -> values over
    `dates`), and optionally `observed` (values over `dates`, or a `(dates, values)`
    pair), `color` and `title`.
    """
    rows = _as_rows(panels, ncols)
    fig, axs = panel_grid(len(rows), len(rows[0]), subfig=subfig,
                          figsize=(figure_width, panel_height * len(rows)), sharex=True)
    for row, cells in enumerate(rows):
        for column, panel in enumerate(cells):
            if panel is None:
                continue
            ax = axs[row, column]
            _quantile_bars(ax, panel["dates"], panel["quantiles"],
                           panel.get("color", "tab:blue"), label="Median")
            observed = panel.get("observed")
            if observed is not None:
                if not isinstance(observed, tuple):
                    observed = (panel["dates"], observed)
                _observations(ax, *observed)
    _finish_grid(fig, axs, rows, ylabels=ylabels)
    return fig, axs


def plot_rolling_forecast_grid(
    panels: Sequence,
    levels: Sequence[float],
    *,
    ncols: int | None = None,
    ylabels: str | Sequence[str] | None = None,
    figure_width: float = DOUBLE_COLUMN,
    panel_height: float = 1.8,
    subfig=None,
):
    """A grid of rolling forecasts: every forecast date's fan, plus what happened.

    Bands rather than bars: one forecast's horizons are one trajectory, so joining them is
    honest. Each panel has `origins` (forecast dates), `horizons` (weeks ahead), `values`
    of shape (origins, horizons, levels), and optionally `observed` (a `(dates, values)`
    pair), `color` and `title`. `panels` is laid out as in `plot_quantile_grid`.
    """
    rows = _as_rows(panels, ncols)
    fig, axs = panel_grid(len(rows), len(rows[0]), subfig=subfig,
                          figsize=(figure_width, panel_height * len(rows)), sharex=True)
    for row, cells in enumerate(rows):
        for column, panel in enumerate(cells):
            if panel is None:
                continue
            ax = axs[row, column]
            values = np.asarray(panel["values"], dtype=np.float64)
            for o, origin in enumerate(panel["origins"]):
                dates = [pd.Timestamp(origin) + pd.Timedelta(days=7 * int(h))
                         for h in panel["horizons"]]
                quantiles = {level: values[o, :, i] for i, level in enumerate(levels)}
                _quantile_bands(ax, dates, quantiles, panel.get("color", "tab:blue"))
            if panel.get("observed") is not None:
                _observations(ax, *panel["observed"])
    _finish_grid(fig, axs, rows, ylabels=ylabels)
    return fig, axs


def plot_line_panels(
    x: Sequence,
    series: Mapping[str, np.ndarray],
    *,
    titles: Sequence[str] | None = None,
    colors: Mapping[str, object] | None = None,
    ylabel: str | None = None,
    xlabel: str | None = None,
    reference: float | None = None,
    reference_label: str = "Nominal",
    xticks: Sequence | None = None,
    ylim: tuple[float, float] | None = None,
    legend_loc: str = "lower left",
    figure_width: float = DOUBLE_COLUMN,
    panel_height: float = 2.1,
    share_y: bool = True,
    subfig=None,
):
    """A row of line panels, one per row of each series, with the legend in the first.

    `series` maps a legend label to an array of shape (panels, len(x)). `reference` is a
    dotted horizontal line, such as a nominal coverage. `share_y=False` for panels on
    different scales. The legend sits inside the first
    panel at `legend_loc`, an explicit corner: matplotlib's `loc="best"` is not stable
    from one run to the next, and an outside legend would collide with a neighbouring
    subfigure's.
    """
    panels = np.asarray(next(iter(series.values()))).shape[0]
    fig, grid = panel_grid(1, panels, subfig=subfig, figsize=(figure_width, panel_height),
                           sharex=True, sharey=share_y)
    axs = grid[0]
    for panel, ax in enumerate(axs):
        for name, values in series.items():
            color = None if colors is None else colors.get(name)
            ax.plot(x, np.asarray(values)[panel], marker="o", markersize=2.5, color=color,
                    label=name)
        if reference is not None:
            ax.axhline(reference, color="black", linestyle=":", linewidth=0.8,
                       label=reference_label)
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

    handles, labels = axs[0].get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    axs[0].legend(list(unique.values()), list(unique), fontsize=6, loc=legend_loc)
    return fig, axs


# The band drawn around each model's median in a single forecast.
SINGLE_FORECAST_INTERVAL = 0.95


def plot_single_forecast_grid(rows, *, colors, ylabels=None, title=None):
    """One forecast from one date, by one or more models, panel by panel.

    The teaching counterpart of `plot_rolling_forecast_grid`: what one forecast produced
    and what then happened. Each panel has `dates` and `observed` (the whole observed
    series), `origin` (the first forecast date: observations before it, which the filter
    saw, are filled; later ones are hollow), `forecast_dates`, `forecasts` (model ->
    {level: values over `forecast_dates`}) and optionally `title`. `colors` maps a model
    to its colour.
    """
    rows = _as_rows(rows)
    nrows, ncols = len(rows), len(rows[0])
    fig, axs = panel_grid(nrows, ncols, figsize=(2.4 * ncols, 1.9 * nrows + 0.5),
                          sharex=True)
    lower = (1.0 - SINGLE_FORECAST_INTERVAL) / 2.0
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
                ax.fill_between(forecast_dates, _level(quantiles, lower),
                                _level(quantiles, 1.0 - lower), color=colors[label],
                                alpha=0.25, linewidth=0)
                ax.plot(forecast_dates, _level(quantiles, 0.5), color=colors[label],
                        linewidth=1.2,
                        label=f"{label}: median, {SINGLE_FORECAST_INTERVAL:.0%} PI")
            ax.set_ylim(bottom=0)

    _finish_grid(fig, axs, rows, ylabels=ylabels, title=title, legend_from=axs[0, 0],
                 label_rotation=45)
    return fig, axs


# --- matrices ---------------------------------------------------------------------


def plot_contact_matrix(ax: Axes, matrix, labels, title=None, norm: Normalize | None = None):
    """A contact matrix as an annotated heatmap: rows the individual, columns the contact.

    Pass panels drawn side by side one shared `norm`, so their colours are comparable.
    Returns the image, for a colorbar.
    """
    image = ax.imshow(matrix, cmap=SEQUENTIAL, norm=norm, aspect="equal")
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

    # Each value in near-black or white, whichever reads against its cell.
    rgba = image.cmap(image.norm(matrix))
    luminance = rgba[..., :3] @ np.array([0.2126, 0.7152, 0.0722])
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=5,
                    color="#0b0b0b" if luminance[i, j] > 0.55 else "#ffffff")
    return image


def plot_flow_matrix(ax: Axes, matrix, groups, group_labels=None, xlabel="destination",
                     ylabel="origin"):
    """An origin-destination flow matrix on a log scale, with group blocks marked.

    `groups` gives each row's group (a state, for counties), and rows must already be
    sorted by it. Log scale because a commuting matrix's diagonal runs two to three orders
    of magnitude above the rest, which would otherwise be invisible. Returns the image.
    """
    groups = np.asarray(groups)
    for group in np.unique(groups):
        positions = np.where(groups == group)[0]
        if positions.size != positions[-1] - positions[0] + 1:
            raise ValueError(f"group {group!r} is not contiguous; sort the rows first")

    image = ax.imshow(np.log10(matrix + 1), cmap=SEQUENTIAL, interpolation="nearest")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    # Separate the blocks, and label each at its centre on the diagonal.
    for boundary in np.where(groups[:-1] != groups[1:])[0] + 0.5:
        ax.axhline(boundary, color="white", linewidth=0.6)
        ax.axvline(boundary, color="white", linewidth=0.6)
    if group_labels is not None:
        for group, label in zip(np.unique(groups), group_labels):
            centre = float(np.where(groups == group)[0].mean())
            ax.text(centre, centre, label, ha="center", va="center", fontsize=7,
                    color="white", fontweight="bold",
                    path_effects=[pe.withStroke(linewidth=1.6, foreground="black")])
    return image


# --- distributions ----------------------------------------------------------------


def _swarm_offsets(values: np.ndarray, width: float = 0.30, bins: int = 24) -> np.ndarray:
    """Vertical offsets that spread overlapping points into a symmetric swarm.
    Deterministic, unlike jitter, so a rebuilt figure is the same figure."""
    values = np.asarray(values, dtype=float)
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
        offsets[members] = (np.arange(count) - (count - 1) / 2) / max(count - 1, 1) * spread
    return offsets


def plot_ratio_swarm(ax: Axes, rows: Sequence[Mapping], *, ticks: Sequence[float]) -> None:
    """One row per model, one point per unit (state, county) per seed, on a log ratio axis.

    Each row has `label`, `color` and `seeds`: one array of ratios per seed, units in the
    same order. Both seeds are drawn, joined by a line, rather than a point and a range,
    which for two replicates would look better powered than it is; each seed's median is
    a tick on its own half of the row, so two nearly equal medians stay distinguishable.
    """
    labels = []
    for index, row in enumerate(rows):
        seeds = [np.asarray(s, dtype=float) for s in row["seeds"]]
        colour = row["color"]
        base = len(rows) - 1 - index
        # Each unit sits at its geometric mean over seeds, whichever seed is drawn.
        centre = np.exp(np.mean([np.log(s) for s in seeds], axis=0))
        y = base + _swarm_offsets(centre)

        if len(seeds) > 1:
            ax.hlines(y, np.min(seeds, axis=0), np.max(seeds, axis=0),
                      color=colour, linewidth=0.6, alpha=0.5, zorder=1)
        ax.scatter(np.concatenate(seeds), np.tile(y, len(seeds)),
                   s=5.5, color=colour, zorder=3, linewidth=0)

        for position, ratios in enumerate(seeds):
            low = base + (0.02 if position == 0 else -0.46)
            ax.vlines(np.median(ratios), low, low + 0.44, color=colour, linewidth=1.2,
                      zorder=4)
        ax.text(float(np.median(centre)), base + 0.47,
                " / ".join(f"{np.median(s):.2f}" for s in seeds),
                color=colour, fontsize=6, ha="center", va="bottom")

        wins = " / ".join(str(int((s < 1.0).sum())) for s in seeds)
        labels.append(f"{row['label']}\nbetter in {wins} of {seeds[0].size}")

    ax.axvline(1.0, color="black", linewidth=0.9, zorder=2)
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
