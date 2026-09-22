"""Read what `run_season` wrote.

Deliberately disease-agnostic: it knows the output layout and nothing about any one
demo. Both the evaluation notebook and the manuscript exporter load through here, so a
figure in the paper and the same figure in a notebook come from identical numbers.

`quantile_array` is the workhorse. Every output file is tidy with a `quantile` column,
so one pivot serves forecasts, the season fit and the estimated parameters alike, and
the arrays it returns are the shape `manuscript_analysis.demos.lib.scoring` expects.
"""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd

__all__ = [
    "RunOutputs",
    "align_observations",
    "load_observations",
    "load_run",
    "load_runs",
    "quantile_array",
]


class RunOutputs(NamedTuple):
    """One model's outputs, as written by `manuscript_analysis.demos.lib.cli.run_season_cli`."""

    name: str
    info: dict
    """`run.json`: season, realizations, window, seed, elapsed time."""
    forecasts: pd.DataFrame
    fit: pd.DataFrame
    params: pd.DataFrame


def load_run(folder: str | Path) -> RunOutputs:
    """Load one model's output folder."""
    folder = Path(folder)
    info = json.loads((folder / "run.json").read_text())

    files = sorted((folder / "forecasts").glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"no forecast files in {folder / 'forecasts'}")
    forecasts = pd.concat(
        [pd.read_csv(f, dtype={"location": str},
                     parse_dates=["reference_date", "target_end_date"])
         for f in files],
        ignore_index=True,
    )
    fit = pd.read_csv(folder / "fit.csv", dtype={"location": str},
                      parse_dates=["target_end_date"])
    params = pd.read_csv(folder / "params.csv", dtype={"location": str},
                         parse_dates=["date"])
    return RunOutputs(info["model"], info, forecasts, fit, params)


def load_runs(root: str | Path, names: Sequence[str] | None = None) -> dict[str, RunOutputs]:
    """Load every model under `root`, or just `names`, in the order given."""
    root = Path(root)
    if names is None:
        names = sorted(p.parent.name for p in root.glob("*/run.json"))
    missing = [n for n in names if not (root / n / "run.json").exists()]
    if missing:
        raise FileNotFoundError(
            f"no output for {', '.join(missing)} under {root}; run them first"
        )
    return {name: load_run(root / name) for name in names}


def load_observations(path: str | Path) -> pd.DataFrame:
    """The frozen observations every model was fitted and scored against."""
    return pd.read_csv(path, dtype={"location": str}, parse_dates=["date"])


def quantile_array(
    frame: pd.DataFrame,
    dims: Sequence[str],
    *,
    levels: Sequence[float] | None = None,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Pivot a tidy quantile frame into an array with quantiles on the last axis.

    Parameters
    ----------
    dims :
        Columns to index the leading axes by, in order.
    levels :
        Quantile levels to keep, in order. Defaults to every level present, sorted.

    Returns
    -------
    :
        The array, shape `(*dim sizes, len(levels))`, and the label of every
        coordinate along each dim.
    """
    if frame.empty:
        raise ValueError(
            f"no rows to pivot by {list(dims)}; a filter above this removed everything"
        )

    frame = frame.copy()
    if levels is None:
        levels = np.sort(frame["quantile"].unique())
    else:
        levels = np.asarray(levels, dtype=float)
        frame = frame[np.isin(frame["quantile"].round(10), levels.round(10))]

    if frame.empty:
        raise ValueError(
            f"no rows left after selecting levels {list(levels)}; "
            f"the file holds {sorted(np.unique(frame['quantile']))}"
        )

    coords = {dim: np.sort(frame[dim].unique()) for dim in dims}
    expected = int(np.prod([len(v) for v in coords.values()]) * len(levels))
    if len(frame) != expected:
        raise ValueError(
            f"expected {expected} rows for a complete {dims} x quantile grid, "
            f"got {len(frame)}; the output is incomplete or has duplicates"
        )

    ordered = frame.sort_values([*dims, "quantile"])
    shape = (*(len(coords[dim]) for dim in dims), len(levels))
    return ordered["value"].to_numpy().reshape(shape), coords


def align_observations(
    frame: pd.DataFrame,
    dims: Sequence[str],
    observations: pd.DataFrame,
    *,
    quantity: str,
    date_col: str = "target_end_date",
) -> np.ndarray:
    """Observed values laid out to match `quantile_array(frame, dims)`.

    The join is on each cell's own `date_col` and location, never on positional
    arithmetic, so a forecast can only be scored against the week it predicted. That
    matters here because a rolling origin predicts the same week from several origins,
    so the date is not one of `dims`.
    """
    # `location` is usually one of `dims`; keep the column list unique either way.
    columns = list(dict.fromkeys([*dims, date_col, "location"]))
    cells = frame.drop_duplicates(subset=list(dims))[columns].sort_values(list(dims))

    lookup = observations[observations["quantity"] == quantity]
    lookup = lookup.set_index(["date", "location"])["value"]
    keys = pd.MultiIndex.from_arrays(
        [pd.to_datetime(cells[date_col]), cells["location"]]
    )
    values = lookup.reindex(keys).to_numpy(dtype=float)

    if np.isnan(values).any():
        n = int(np.isnan(values).sum())
        raise ValueError(
            f"{n} of {values.size} cells have no matching observation for quantity "
            f"{quantity!r}; check the season window"
        )
    shape = tuple(frame[dim].nunique() for dim in dims)
    if values.size != int(np.prod(shape)):
        raise ValueError(
            f"expected {int(np.prod(shape))} cells for {dims}, got {values.size}"
        )
    return values.reshape(shape)
