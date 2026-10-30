"""A run on disk: one model at one seed, its rolling forecasts written as tidy CSV.

A run folder holds

    forecasts/<reference date>.csv   one file per forecast date
    fit.csv                          the filter's weekly fit, before and after each update
    params.csv                       the estimated parameters, day by day
    run.json                         the settings, written last

Every file is quantiles in long form, one row per quantile level, in the hub format
FluSight uses. `run.json` is written last, so a folder that has one is complete.
"""

import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike


def quantiles(ensemble: np.ndarray, levels: Iterable[float]) -> np.ndarray:
    """Quantiles across the realizations (axis 0), as a new last axis.

    One `np.quantile` per level: epymorph's own summaries take only levels in steps of
    2.5%, and FluSight's include 1% and 99%.
    """
    return np.stack([np.quantile(ensemble, level, axis=0) for level in levels], axis=-1)


def quantile_table(values: np.ndarray, levels: Iterable[float], axes: Mapping[str, ArrayLike]) -> pd.DataFrame:
    """Melt a quantile array into tidy rows.

    `axes` names the leading axes of `values` in order, with each one's labels; the last
    axis is the quantile level.
    """
    labels = [np.asarray(axis) for axis in axes.values()] + [np.asarray(levels)]
    grids = np.meshgrid(*labels, indexing="ij")
    columns = {name: grid.ravel() for name, grid in zip([*axes, "quantile"], grids)}
    columns["value"] = values.ravel()
    return pd.DataFrame(columns)


def forecast_table(
    reference_date: np.datetime64,
    target: str,
    scales: Mapping[str, tuple[np.ndarray, Sequence[str]]],
    quantities: Sequence[str],
    levels: Iterable[float],
) -> pd.DataFrame:
    """One forecast date's file.

    `scales` maps a scale name to `(values, locations)`, with `values` shaped
    `(horizons, locations, quantities, levels)`. Demo 2 writes two: `scored`, the three
    states every model is compared at, and for the county models `model`, the same
    forecast at their own counties. A `scale` column tells them apart, so nothing reading
    the file can mix a state and a county by accident. Demo 1 has one scale, and passes
    it as `None`: its files have no `scale` column.
    """
    with_scale = list(scales) != [None]
    blocks = []
    for scale, (values, locations) in scales.items():
        horizons = np.arange(values.shape[0])
        block = quantile_table(
            values, levels,
            {"horizon": horizons, "location": locations, "quantity": quantities},
        )
        if with_scale:
            block.insert(0, "scale", scale)
        blocks.append(block)
    table = pd.concat(blocks, ignore_index=True)
    table.insert(0, "reference_date", str(reference_date))
    table["target_end_date"] = [
        str(reference_date + np.timedelta64(7 * int(h), "D")) for h in table["horizon"]
    ]
    table["target"] = target
    columns = ["reference_date", "target", "horizon", "target_end_date", "location",
               *(["scale"] if with_scale else []), "quantity", "quantile", "value"]
    sort_keys = [*(["scale"] if with_scale else []), "horizon", "location", "quantity", "quantile"]
    return table[columns].sort_values(sort_keys)


def with_total(ensemble: np.ndarray, levels: Iterable[float]) -> np.ndarray:
    """Quantiles of each quantity, then of their sum, as one more quantity.

    The sum is taken within each realization before any quantile, because quantiles do
    not add: the sum of six age groups' medians is not the median of the total.
    """
    each = quantiles(ensemble, levels)
    total = quantiles(ensemble.sum(axis=-1), levels)
    return np.concatenate([each, total[..., np.newaxis, :]], axis=-2)


def fit_table(
    posterior: np.ndarray,
    prior: np.ndarray,
    dates: np.ndarray,
    locations: Sequence[str],
    quantities: Sequence[str],
    levels: Iterable[float],
    add_total: bool = False,
) -> pd.DataFrame:
    """`fit.csv`: the filter's weekly fit at the model's own nodes.

    `posterior` is after each week's update, so it is a fit; `prior` is before it, so it is
    a genuine one-week-ahead prediction. Both are `(realizations, weeks, nodes, quantities)`.
    `add_total` adds the quantities' sum as a quantity named `total` (see `with_total`).
    """
    tables = []
    for series, ensemble in (("posterior", posterior), ("prior", prior)):
        values = with_total(ensemble, levels) if add_total else quantiles(ensemble, levels)
        names = [*quantities, "total"] if add_total else list(quantities)
        table = quantile_table(
            values, levels,
            {"target_end_date": dates, "location": locations, "quantity": names},
        )
        table.insert(0, "series", series)
        tables.append(table)
    return pd.concat(tables, ignore_index=True)


def params_table(
    params: np.ndarray,
    dates: np.ndarray,
    locations: Sequence[str],
    names: Sequence[str],
    levels: Iterable[float],
) -> pd.DataFrame:
    """`params.csv`: the estimated parameters, `(realizations, days, nodes, parameters)`,
    on the scale the filter estimates them (here, log)."""
    return quantile_table(
        quantiles(params, levels),
        levels,
        {"date": dates, "location": locations, "parameter": names},
    )


def run_on_disk(folder: Path, settings: Mapping[str, object]) -> bool:
    """Whether `folder` holds a finished run made with these `settings`.

    A run made with different settings does not count: reusing it would quietly score a
    run that answers a different question.
    """
    info_file = Path(folder) / "run.json"
    if not info_file.exists():
        return False
    stored = json.loads(info_file.read_text())
    return all(stored.get(key) == value for key, value in settings.items())


def write_run(
    folder: Path,
    *,
    forecasts: Sequence[pd.DataFrame],
    fit: pd.DataFrame,
    params: pd.DataFrame,
    info: Mapping[str, object],
) -> Path:
    """Write one run, `run.json` last."""
    folder = Path(folder)
    (folder / "forecasts").mkdir(parents=True, exist_ok=True)
    for table in forecasts:
        reference_date = table["reference_date"].iloc[0]
        table.to_csv(folder / "forecasts" / f"{reference_date}.csv", index=False)
    fit.to_csv(folder / "fit.csv", index=False)
    params.to_csv(folder / "params.csv", index=False)
    (folder / "run.json").write_text(json.dumps(dict(info), indent=2, default=str))
    return folder


# --- reading runs back ----------------------------------------------------------------


class Run(NamedTuple):
    """One run as read back from disk."""

    name: str
    info: dict
    forecasts: pd.DataFrame
    fit: pd.DataFrame
    params: pd.DataFrame


def load_run(folder: Path) -> Run:
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
    return Run(info["model"], info, forecasts, fit, params)


def load_runs(root: Path, names: Sequence[str]) -> dict[str, Run]:
    """The runs of the models in `names` under `root`, in that order."""
    root = Path(root)
    missing = [name for name in names if not (root / name / "run.json").exists()]
    if missing:
        raise FileNotFoundError(f"no run of {', '.join(missing)} under {root}")
    return {name: load_run(root / name) for name in names}


def quantile_array(frame: pd.DataFrame, dims: Sequence[str], *, levels: Iterable[float]) -> tuple[np.ndarray, dict]:
    """Pivot tidy quantile rows into an array, `dims` then the quantile levels.

    Returns the array and the sorted labels along each of `dims`. Fails if the rows do
    not make a complete grid, which is how a missing or duplicated row is caught.
    """
    levels = np.asarray(levels, dtype=float)
    frame = frame[np.isin(frame["quantile"].round(10), levels.round(10))]
    if frame.empty:
        raise ValueError(f"no rows to pivot by {list(dims)} at levels {list(levels)}")

    coords = {dim: np.sort(frame[dim].unique()) for dim in dims}
    expected = int(np.prod([len(v) for v in coords.values()]) * len(levels))
    if len(frame) != expected:
        raise ValueError(
            f"expected {expected} rows for a complete {list(dims)} x quantile grid, "
            f"got {len(frame)}"
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
    """The observed value for each cell of `quantile_array(frame, dims)`, same shape.

    Joined on each cell's own date and location, never by position, so a forecast can
    only be scored against the week it predicted.
    """
    columns = list(dict.fromkeys([*dims, date_col, "location"]))
    cells = frame.drop_duplicates(subset=list(dims))[columns].sort_values(list(dims))

    lookup = observations[observations["quantity"] == quantity]
    lookup = lookup.set_index(["date", "location"])["value"]
    keys = pd.MultiIndex.from_arrays([pd.to_datetime(cells[date_col]), cells["location"]])
    values = lookup.reindex(keys).to_numpy(dtype=float)
    if np.isnan(values).any():
        raise ValueError(
            f"{int(np.isnan(values).sum())} of {values.size} cells have no observed "
            f"{quantity}; check the season window"
        )
    shape = tuple(frame[dim].nunique() for dim in dims)
    return values.reshape(shape)
