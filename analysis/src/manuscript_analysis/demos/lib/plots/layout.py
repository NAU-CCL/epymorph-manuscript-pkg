"""Laying out a grid of panels, and the finishing a multi-panel figure needs.

Both demos draw the same multi-panel shapes: a grid of small time-series panels, one
per age band, per county, per state, or per quantity. Only the meaning of a row and a
column differs between them, so the layout rules live here and the two demos cannot
drift apart typographically.

The finishing rules, applied once here rather than re-argued in each figure function:

- **x tick labels on the bottom of each column only.** The panels share an x axis, so
  repeating the dates under every row spends ink on nothing and steals height from the
  data. A column whose bottom cell is empty gets its labels back on the lowest panel
  that is actually drawn.
- **y axis labels on the first column only**, one per row, since a row is one quantity.
- **one legend for the whole figure**, outside the axes. Every panel uses the same
  encoding, so per-panel legends are redundant and tend to sit on the data.
"""

from collections.abc import Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np

__all__ = ["as_panel_rows", "finish_panel_grid", "panel_grid"]


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
