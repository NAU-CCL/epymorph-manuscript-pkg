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
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np
import pandas as pd


def quantiles(ensemble: np.ndarray, levels) -> np.ndarray:
    """Quantiles across the realizations (axis 0), as a new last axis.

    One `np.quantile` per level: epymorph's own summaries take only levels in steps of
    2.5%, and FluSight's include 1% and 99%.
    """
    return np.stack([np.quantile(ensemble, level, axis=0) for level in levels], axis=-1)


def quantile_table(values: np.ndarray, levels, axes: Mapping[str, Sequence]) -> pd.DataFrame:
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
    levels,
) -> pd.DataFrame:
    """One forecast date's file.

    `scales` maps a scale name to `(values, locations)`, with `values` shaped
    `(horizons, locations, quantities, levels)`. Demo 2 writes two: `scored`, the three
    states every model is compared at, and for the county models `model`, the same
    forecast at their own counties. A `scale` column tells them apart, so nothing reading
    the file can mix a state and a county by accident.
    """
    blocks = []
    for scale, (values, locations) in scales.items():
        horizons = np.arange(values.shape[0])
        block = quantile_table(
            values, levels,
            {"horizon": horizons, "location": locations, "quantity": quantities},
        )
        block.insert(0, "scale", scale)
        blocks.append(block)
    table = pd.concat(blocks, ignore_index=True)
    table.insert(0, "reference_date", str(reference_date))
    table["target_end_date"] = [
        str(reference_date + np.timedelta64(7 * int(h), "D")) for h in table["horizon"]
    ]
    table["target"] = target
    columns = [
        "reference_date", "target", "horizon", "target_end_date",
        "location", "scale", "quantity", "quantile", "value",
    ]
    return table[columns].sort_values(["scale", "horizon", "location", "quantity", "quantile"])


def fit_table(
    posterior: np.ndarray,
    prior: np.ndarray,
    dates,
    locations: Sequence[str],
    quantities: Sequence[str],
    levels,
) -> pd.DataFrame:
    """`fit.csv`: the filter's weekly fit at the model's own nodes.

    `posterior` is after each week's update, so it is a fit; `prior` is before it, so it is
    a genuine one-week-ahead prediction. Both are `(realizations, weeks, nodes, quantities)`.
    """
    tables = []
    for series, ensemble in (("posterior", posterior), ("prior", prior)):
        table = quantile_table(
            quantiles(ensemble, levels), levels,
            {"target_end_date": dates, "location": locations, "quantity": quantities},
        )
        table.insert(0, "series", series)
        tables.append(table)
    return pd.concat(tables, ignore_index=True)


def params_table(
    params: np.ndarray, dates, locations: Sequence[str], names: Sequence[str], levels
) -> pd.DataFrame:
    """`params.csv`: the estimated parameters, `(realizations, days, nodes, parameters)`,
    on the scale the filter estimates them (here, log)."""
    return quantile_table(
        quantiles(params, levels), levels,
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
