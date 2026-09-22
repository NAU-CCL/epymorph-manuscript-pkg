"""Heatmaps for structure matrices: age mixing, and spatial flows."""

import matplotlib.patheffects as pe
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import Normalize

from manuscript_analysis.demos.lib.figures import SEQUENTIAL


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
