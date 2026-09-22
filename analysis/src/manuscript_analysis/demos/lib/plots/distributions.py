"""Distributions of a per-unit ratio, drawn as a beeswarm.

The shape both demos need for their headline comparison: one row per contrast, one mark
per unit (jurisdiction, county), on a log axis centred on 1. Demo 1 compares two mixing
structures across 51 states; Demo 2 compares movement against no movement across 32
counties, or two quantities across the same counties.
"""

from collections.abc import Mapping, Sequence

import numpy as np
from matplotlib.axes import Axes
from matplotlib.ticker import FixedLocator, NullLocator

__all__ = ["plot_ratio_swarm", "swarm_offsets"]


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
