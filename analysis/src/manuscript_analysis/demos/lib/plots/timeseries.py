"""Quantile-band time series: the recurring figure shape in these demos."""

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from manuscript_analysis.demos.lib.plots.layout import (
    as_panel_rows,
    finish_panel_grid,
    panel_grid,
)


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
