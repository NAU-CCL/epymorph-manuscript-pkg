"""The forecasting-model container, following `../FluSight-pipeline/utils.py`.

A model module builds its RUME once on a `PlaceholderTimeFrame` and its `Observations`
on a `PlaceholderSource`; the runner substitutes the real time frame and source for each
window. Both placeholders exist to make that substitution obvious at the call site.

The rolling-origin loop and the output writers live here too (phase 3).
"""

import dataclasses
import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Literal, NamedTuple

import numpy as np
import pandas as pd
from epymorph.attribute import NamePattern
from epymorph.forecasting.ensemble_kalman_filter import EnsembleKalmanFilterSimulator
from epymorph.forecasting.filter import Observations
from epymorph.forecasting.forecast import ForecastSimulator
from epymorph.forecasting.pipeline import PipelineConfig, UnknownParam
from epymorph.rume import RUME
from epymorph.time import TimeFrame
from epymorph.util import DateValueType

__all__ = [
    "TOTAL_QUANTITY",
    "Disease",
    "ForecastModel",
    "PlaceholderSource",
    "PlaceholderTimeFrame",
    "Quantity",
    "RollingOrigin",
    "run_rolling_origin",
    "write_outputs",
]

TOTAL_QUANTITY = "total"
"""The label for the summed-quantities row in every output file."""

Disease = Literal["Covid", "Influenza", "RSV"]


class Quantity(NamedTuple):
    """One observed channel: where it lives in a result, and how a week of it is formed.

    Demo 1's six age bands are all `I -> H` events summed over the week. Demo 2 observes a
    hospital **census**, which is a compartment and whose weekly value is the **mean**, and
    **deaths**, which is an event and whose weekly value is the **sum**. Summing a stock
    over seven days would multiply it by seven, so the distinction is not cosmetic.
    """

    name: str
    """Must match the `quantities` entry at the same position."""

    source: Literal["events", "compartments"]
    index: int
    """Position along that array's last axis."""

    weekly: Literal["sum", "mean"]
    """`sum` for a flow, `mean` for a stock."""


@dataclass(frozen=True, init=False)
class PlaceholderTimeFrame(TimeFrame):
    """A RUME's `time_frame` before the runner replaces it with the real window."""

    def __init__(self):
        object.__setattr__(self, "start_date", date.min)
        object.__setattr__(self, "duration_days", 1)
        object.__setattr__(self, "end_date", date.min + timedelta(1))


@dataclass(frozen=True)
class PlaceholderSource(np.ndarray):
    """An `Observations.source` before the runner replaces it with the real data."""

    def __new__(cls):
        return super().__new__(cls, shape=(0,), dtype=DateValueType)


@dataclass(frozen=True)
class ForecastModel:
    """One model in a comparison: everything needed to fit and forecast it."""

    name: str
    """Identifies the model in output paths and figures; must be filesystem-safe."""

    disease: Disease

    rume: RUME
    """Built on a `PlaceholderTimeFrame`."""

    unknown_params: Mapping[NamePattern | str, UnknownParam]

    observations: Observations
    """Built on a `PlaceholderSource`."""

    quantities: tuple[str, ...]
    """Names of the Q axis, in order, matching `ModelLink.quantity`."""

    observations_source: Callable[[], np.ndarray] | None = None
    """Returns this model's observations as a date-value array, loaded on demand.

    The model knows which quantities it observes, so it knows which source it wants;
    the runner stays ignorant of any one demo's data. Called once per run.
    """

    initial_values_factory: (
        Callable[[int, np.random.Generator], np.ndarray] | None
    ) = None
    """`(num_realizations, rng) -> (R, N, C)`, where C is `len(quantities) * compartments`.

    `None` means the runner warms the model up from the RUME's own initializer instead.
    """

    channels: tuple[Quantity, ...] | None = None
    """How to read each quantity out of a simulation result.

    `None` means every quantity is its stratum's `I -> H` event summed over the week, which
    is Demo 1's shape and is derived from `rume.ipm.events` by name.
    """

    aggregate_quantities: bool = True
    """Whether summing the Q axis within a realization is meaningful.

    True for Demo 1: six age bands add to a statewide total. **False for Demo 2**: a
    hospital census and a death count do not add to anything. Independent of
    `scoring_groups`, which aggregates the *node* axis; see
    `demo-covid/refactor-plan-v01.md`.
    """

    scoring_groups: Mapping[str, Sequence[int]] | None = None
    """Output location -> the model node indices it covers, summed within a realization.

    `None` scores at the model's own nodes, which is Demo 1 and Demo 2's state model.
    Demo 2's county models pass `{"25": [...], "09": [...], "33": [...]}` to score 32
    counties as 3 states. Quantiles do not add, so the sum happens before quantiling.

    This applies to the **forecast only**. The season fit stays at the model's own nodes,
    because that is the scale its observations and its likelihood live at.
    """

    forecast_dynamics: Callable[[object], Mapping[str, object]] | None = None
    """Called with the filter output at each origin, returning `override_dynamics`.

    `None` forecasts with the filter's fitted parameters unchanged, which is Demo 1.
    Demo 2 re-derives the OU mean and spread from the filter's own ensemble, because
    carrying filtering inflation into a forecast is a category error.
    """

    movement_data_mode: str | None = None
    """Passed to both simulators when set. Demo 2 uses `"home"`; Demo 1 sets nothing."""

    forecast_seed: Callable[[int, int], int] | None = None
    """`(seed, origin_position) -> rng seed` for the forecast branch.

    `None` keeps Demo 1's behaviour, `seed + 1` at every origin, which is what produced the
    settled Demo 1 numbers and must not change. Demo 2 passes
    `lambda seed, position: seed + 1 + position`, matching `covid-v04.ipynb`, so the
    forecast noise is not identical across origins.
    """

    @property
    def multi_quantity(self) -> bool:
        """Whether this model observes more than one quantity per node."""
        return len(self.quantities) > 1


class RollingOrigin(NamedTuple):
    """Quantile forecasts and the season fit, from one rolling-origin run."""

    quantile_levels: np.ndarray
    reference_dates: np.ndarray
    """(O,) the observation date labelling each origin's first forecast week."""
    forecast: np.ndarray
    """(O, H, N, Q, L) per-quantity forecast quantiles."""
    forecast_total: np.ndarray | None
    """(O, H, N, L) summed-quantities forecast quantiles, or None.

    Taken from the same ensemble as `forecast`, summing the Q axis within each
    realization first, because quantiles do not add. Only meaningful when the
    quantities are commensurate, as age strata are but a census and deaths are not;
    see `demo-covid/refactor-plan-v01.md`.
    """
    forecast_nodes: np.ndarray | None
    """(O, H, N_model, Q, L) the SAME forecast at the model's own nodes, or None.

    Only present when `scoring_groups` coarsens the geography; without grouping the
    scored nodes already are the model's nodes. Quantiled per node before any grouping,
    so this is a genuine per-node forecast and not a decomposition of the aggregate,
    which could not be recovered after the fact.
    """
    fit_dates: np.ndarray
    """(W,) week-ending dates of the assimilated window."""
    posterior: np.ndarray
    """(W, N, Q, L) weekly fit quantiles, after the Kalman update."""
    posterior_total: np.ndarray | None
    """(W, N, L), or None when the quantities do not add."""
    prior: np.ndarray
    """(W, N, Q, L) weekly one-week-ahead prediction quantiles, before the update."""
    prior_total: np.ndarray | None
    """(W, N, L), or None when the quantities do not add."""
    param_dates: np.ndarray
    """(D,) days of the assimilated window."""
    param_names: tuple[str, ...]
    params: np.ndarray
    """(D, N, P, L) estimated-parameter quantiles, on the filter's own (log) scale."""


def _event_indices(rume: RUME, quantities: Sequence[str]) -> list[int]:
    """Where each observed quantity's `I -> H` event sits in `rume.ipm.events`."""
    if tuple(quantities) == (TOTAL_QUANTITY,):
        names = ["I → H"]
    else:
        names = [f"I_{name} → H_{name}" for name in quantities]
    indices = []
    for name in names:
        matches = [i for i, e in enumerate(rume.ipm.events) if str(e.name) == name]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one event named {name!r}")
        indices.append(matches[0])
    return indices


def _channels(model: "ForecastModel", rume: RUME) -> tuple[Quantity, ...]:
    """The model's own channel spec, or Demo 1's event-per-stratum default."""
    if model.channels is not None:
        names = tuple(c.name for c in model.channels)
        if names != tuple(model.quantities):
            raise ValueError(
                f"channels {names} do not match quantities {tuple(model.quantities)}"
            )
        return model.channels
    return tuple(
        Quantity(name=name, source="events", index=index, weekly="sum")
        for name, index in zip(
            model.quantities, _event_indices(rume, model.quantities)
        )
    )


def _weekly_values(
    result, channels: Sequence[Quantity], weeks: int, nodes: int
) -> np.ndarray:
    """`(R, weeks, N, Q)` from a simulation result, one slice per channel.

    Ticks are per TAU, not per day, and a movement model with two steps a day yields twice
    as many as one with a single step, so the factor is **derived from the result** rather
    than assumed. Demo 1 previously hardcoded seven.
    """
    realizations, ticks = result.events.shape[0], result.events.shape[1]
    taus_per_day, remainder = divmod(ticks, 7 * weeks)
    if remainder or taus_per_day < 1:
        raise ValueError(
            f"{ticks} ticks is not a whole number of taus over {weeks} weeks x 7 days"
        )
    shape = (realizations, weeks, 7 * taus_per_day, nodes)

    series = []
    for channel in channels:
        source = result.events if channel.source == "events" else result.compartments
        block = source[..., channel.index].reshape(shape)
        series.append(block.sum(axis=2) if channel.weekly == "sum" else block.mean(axis=2))
    return np.stack(series, axis=-1)


def _group_nodes(
    ensemble: np.ndarray, groups: Mapping[str, Sequence[int]] | None
) -> np.ndarray:
    """Sum the node axis of `(R, weeks, N, Q)` into scoring groups, within a realization.

    Quantiles do not add, which is why this happens before any quantile is taken. It is
    the same operation the quantity aggregate performs, one axis over.
    """
    if groups is None:
        return ensemble
    return np.stack(
        [ensemble[:, :, list(members), :].sum(axis=2) for members in groups.values()],
        axis=2,
    )


def _quantiles(ensemble: np.ndarray, levels: np.ndarray) -> np.ndarray:
    """Quantiles along axis 0, moved to the last axis."""
    return np.stack([np.quantile(ensemble, q, axis=0) for q in levels], axis=-1)


def run_rolling_origin(
    model: ForecastModel,
    source: np.ndarray,
    *,
    start_date: date,
    num_weeks: int,
    burn_in_weeks: int,
    horizon_weeks: int,
    num_realizations: int,
    quantile_levels: Sequence[float],
    seed: int = 0,
    progress: bool = True,
) -> RollingOrigin:
    """Burn in, then alternate: forecast `horizon_weeks`, assimilate one more week.

    `source` is a date-value array shaped `(T, N)` or `(T, N, Q)`.

    Every week is labelled with the observation date it is fitted or scored against,
    taken from `source` itself, so labels cannot drift from the data. A forecast's
    `reference_date` is therefore the label of its first forecast week.

    Each origin is seeded from `seed` afresh rather than from a threaded generator, so
    any one origin can be reproduced on its own. This follows the notebook harness this
    replaces, not `../FluSight-pipeline`, which threads a single `rng`.

    `progress` prints one line per origin. A large run takes hours and writes nothing
    until it finishes, so without this there is no way to tell a slow run from a stuck
    one.
    """
    # Labels come from the data, never from arithmetic on start_date.
    week_dates = source["date"]
    while week_dates.ndim > 1:
        week_dates = week_dates[..., 0]
    levels = np.asarray(quantile_levels, dtype=np.float64)
    quantities = model.quantities
    num_quantities = len(quantities)

    # The model's ModelLink was built on a PlaceholderTimeFrame; reusing it across real
    # windows is verified to give identical results to rebuilding it (2026-09-15).
    observations = Observations(
        source=source,
        model_link=model.observations.model_link,
        likelihood=model.observations.likelihood,
    )

    burn_in = TimeFrame.of(start_date=start_date, duration_days=7 * burn_in_weeks)
    rume = dataclasses.replace(model.rume, time_frame=burn_in)
    channels = _channels(model, rume)

    # Only passed when the model asks for it, so Demo 1's calls are byte-for-byte what
    # they were before this argument existed.
    extra = (
        {} if model.movement_data_mode is None
        else {"movement_data_mode": model.movement_data_mode}
    )
    forecast_seed = model.forecast_seed or (lambda seed, position: seed + 1)
    scoring_nodes = (
        rume.scope.nodes if model.scoring_groups is None else len(model.scoring_groups)
    )

    if model.initial_values_factory is None:
        raise ValueError(f"{model.name} has no initial_values_factory")

    filter_output = EnsembleKalmanFilterSimulator(
        config=PipelineConfig.from_rume(
            rume=rume,
            num_realizations=num_realizations,
            unknown_params=model.unknown_params,
            initial_values=model.initial_values_factory(
                num_realizations, np.random.default_rng(seed)
            ),
        ),
        observations=observations,
        **extra,
    ).run(rng=np.random.default_rng(seed))

    param_names = tuple(sorted(str(n) for n in filter_output.estimated_params))

    def harvest(result, weeks):
        """The filter's own output over the window it just assimilated.

        `posterior_values` is taken after the Kalman update, so it is a fit. The weekly
        sum of `events` is taken before it, so it is a genuine one-week-ahead forecast.
        """
        prior = _weekly_values(result, channels, weeks, rume.scope.nodes)
        params = np.stack(
            [
                result.estimated_params[name]
                for name in sorted(result.estimated_params, key=str)
            ],
            axis=-1,
        )
        return result.posterior_values, prior, params

    posterior_blocks, prior_blocks, param_blocks = [], [], []
    for block, target in zip(
        harvest(filter_output, burn_in_weeks),
        (posterior_blocks, prior_blocks, param_blocks),
    ):
        target.append(block)

    origins = list(range(burn_in_weeks, num_weeks - horizon_weeks + 1))
    forecast = np.zeros(
        (len(origins), horizon_weeks, scoring_nodes, num_quantities, levels.size)
    )
    forecast_total = np.zeros(
        (len(origins), horizon_weeks, scoring_nodes, levels.size)
    )
    grouped = model.scoring_groups is not None
    forecast_nodes = np.zeros(
        (len(origins), horizon_weeks, rume.scope.nodes, num_quantities, levels.size)
    ) if grouped else None
    reference_dates = []

    started = time.monotonic()
    for position, origin in enumerate(origins):
        if progress:
            done = time.monotonic() - started
            eta = (done / position * (len(origins) - position)) if position else None
            note = f"  eta {eta / 60:5.1f} min" if eta else ""
            print(f"  origin {position + 1:>3}/{len(origins)}  week {origin:>3}"
                  f"  elapsed {done / 60:5.1f} min{note}", flush=True)
        overrides = (
            {} if model.forecast_dynamics is None
            else {"override_dynamics": model.forecast_dynamics(filter_output)}
        )
        forecast_output = ForecastSimulator(
            PipelineConfig.from_output(
                filter_output, extend_duration=7 * horizon_weeks, **overrides
            ),
            **extra,
        ).run(rng=np.random.default_rng(forecast_seed(seed, position)))

        weekly = _weekly_values(
            forecast_output, channels, horizon_weeks, rume.scope.nodes
        )
        scored = _group_nodes(weekly, model.scoring_groups)

        forecast[position] = _quantiles(scored, levels)
        if forecast_nodes is not None:
            forecast_nodes[position] = _quantiles(weekly, levels)
        if model.aggregate_quantities:
            forecast_total[position] = _quantiles(scored.sum(axis=-1), levels)
        reference_dates.append(week_dates[origin])

        if origin != origins[-1]:
            extended = PipelineConfig.from_output(filter_output, 7)
            filter_output = EnsembleKalmanFilterSimulator(
                config=extended, observations=observations, **extra
            ).run(rng=np.random.default_rng(seed))
            for block, target in zip(
                harvest(filter_output, 1),
                (posterior_blocks, prior_blocks, param_blocks),
            ):
                target.append(block)

    posterior = np.concatenate(posterior_blocks, axis=1)
    prior = np.concatenate(prior_blocks, axis=1)
    params = np.concatenate(param_blocks, axis=1)

    fit_weeks = posterior.shape[1]
    fit_dates = week_dates[:fit_weeks]
    param_dates = np.array(
        [
            np.datetime64(start_date + timedelta(days=day))
            for day in range(params.shape[1])
        ]
    )

    return RollingOrigin(
        quantile_levels=levels,
        reference_dates=np.array(reference_dates),
        forecast=forecast,
        forecast_total=forecast_total if model.aggregate_quantities else None,
        forecast_nodes=forecast_nodes,
        fit_dates=fit_dates,
        posterior=_quantiles(posterior, levels),
        posterior_total=(
            _quantiles(posterior.sum(axis=-1), levels)
            if model.aggregate_quantities else None
        ),
        prior=_quantiles(prior, levels),
        prior_total=(
            _quantiles(prior.sum(axis=-1), levels)
            if model.aggregate_quantities else None
        ),
        param_dates=param_dates,
        param_names=param_names,
        params=_quantiles(params, levels),
    )


def _long_frame(
    values: np.ndarray,
    levels: np.ndarray,
    locations: Sequence[str],
    quantities: Sequence[str],
    index: Mapping[str, np.ndarray],
) -> pd.DataFrame:
    """Melt a `(..., N, Q, L)` quantile array into tidy rows.

    `index` names the leading axes, in order, and gives each one's labels.
    """
    axes = [*index.values(), np.asarray(locations), np.asarray(quantities), levels]
    names = [*index.keys(), "location", "quantity", "quantile"]
    grids = np.meshgrid(*axes, indexing="ij")
    columns = {name: grid.ravel() for name, grid in zip(names, grids)}
    columns["value"] = values.ravel()
    return pd.DataFrame(columns)


def _with_total(per_quantity: np.ndarray, total: np.ndarray) -> np.ndarray:
    """Append the summed-quantities aggregate as one more row of the Q axis."""
    return np.concatenate([per_quantity, total[..., np.newaxis, :]], axis=-2)


def write_outputs(
    result: RollingOrigin,
    model: ForecastModel,
    output_folder: Path,
    *,
    locations: Sequence[str],
    scoring_locations: Sequence[str] | None = None,
    run_info: Mapping[str, object] | None = None,
) -> Path:
    """Write one model's forecasts, season fit, parameters and provenance.

    Layout, following `../FluSight-pipeline` with a `quantity` column added:

    - `forecasts/<reference_date>.csv`, one file per origin
    - `fit.csv`, `params.csv`, `run.json`

    The summed-quantities aggregate is written as a `quantity` of `"total"`.
    """
    output_folder = Path(output_folder)
    (output_folder / "forecasts").mkdir(parents=True, exist_ok=True)

    # A single-quantity model already IS its own total; appending the aggregate would
    # write a duplicate row under the same label. A model whose quantities do not add
    # (Demo 2's census and deaths) gets no total row at all.
    aggregated = model.multi_quantity and model.aggregate_quantities
    if model.multi_quantity:
        quantities = [*model.quantities, TOTAL_QUANTITY] if aggregated else [
            *model.quantities
        ]
    else:
        quantities = [TOTAL_QUANTITY]
    horizons = np.arange(result.forecast.shape[1])

    # The forecast may be scored at a coarser geography than the fit; see
    # `ForecastModel.scoring_groups`.
    forecast_locations = (
        list(model.scoring_groups) if model.scoring_groups is not None
        else list(scoring_locations or locations)
    )
    if len(forecast_locations) != result.forecast.shape[2]:
        raise ValueError(
            f"{len(forecast_locations)} scoring locations for "
            f"{result.forecast.shape[2]} forecast nodes"
        )

    # Demo 1's runs were written before the `scale` column existed, and MANIFEST.sha256
    # holds them without it; Demo 2's carry it. Restored 2026-10-07 so that both demos
    # reproduce byte for byte. The restructure gives each demo its own writer, which
    # retires this switch.
    columns = [
        "reference_date", "target", "horizon", "target_end_date",
        "location", "scale", "quantity", "quantile", "value",
    ]
    sort_keys = ["scale", "horizon", "location", "quantity", "quantile"]
    if model.disease == "Influenza":
        columns.remove("scale")
        sort_keys.remove("scale")

    for position, reference_date in enumerate(result.reference_dates):
        # Two resolutions of the same forecast when the geography is coarsened for
        # scoring, told apart by an explicit `scale` column rather than by the shape of
        # the FIPS code. A loader that pivoted on `location` alone would silently build
        # one ragged array spanning both scales, which is the exact error a demo about
        # spatial scale should not ship.
        blocks = []
        for scale, values, places in (
            ("scored", result.forecast[position], forecast_locations),
            ("model", None if result.forecast_nodes is None
             else result.forecast_nodes[position], list(locations)),
        ):
            if values is None:
                continue
            # The summed-quantities aggregate is computed at the SCORED nodes only, so
            # it cannot be appended to the model-scale block; its node axis is the wrong
            # length. No current model both groups nodes and adds quantities, but the
            # shapes would collide silently if one did.
            if aggregated and scale == "scored":
                values = _with_total(values, result.forecast_total[position])
            block = _long_frame(
                values,
                result.quantile_levels,
                places,
                quantities,
                {"horizon": horizons},
            )
            block.insert(0, "scale", scale)
            blocks.append(block)
        frame = pd.concat(blocks, ignore_index=True)
        frame.insert(0, "reference_date", str(reference_date))
        frame["target_end_date"] = [
            str(reference_date + np.timedelta64(7 * int(h), "D"))
            for h in frame["horizon"]
        ]
        frame["target"] = f"wk inc {model.disease.lower()} hosp"
        frame[columns].sort_values(sort_keys).to_csv(
            output_folder / "forecasts" / f"{reference_date}.csv", index=False
        )

    fits = []
    for label, per_quantity, total in (
        ("posterior", result.posterior, result.posterior_total),
        ("prior", result.prior, result.prior_total),
    ):
        values = _with_total(per_quantity, total) if aggregated else per_quantity
        frame = _long_frame(
            values,
            result.quantile_levels,
            locations,
            quantities,
            {"target_end_date": result.fit_dates},
        )
        frame.insert(0, "series", label)
        fits.append(frame)
    pd.concat(fits, ignore_index=True).to_csv(
        output_folder / "fit.csv", index=False
    )

    _long_frame(
        result.params,
        result.quantile_levels,
        locations,
        result.param_names,
        {"date": result.param_dates},
    ).rename(columns={"quantity": "parameter"}).to_csv(
        output_folder / "params.csv", index=False
    )

    info = {
        "model": model.name,
        "disease": model.disease,
        "quantities": list(model.quantities),
        # The structural knobs belong in the run record, not in a cache key that has to
        # be remembered: the folder is the artifact. See `demo-covid/refactor-plan-v01.md`
        # on the cache hazard this replaces.
        "aggregate_quantities": model.aggregate_quantities,
        "scoring_locations": forecast_locations,
        "movement_data_mode": model.movement_data_mode,
        "forecast_dynamics": model.forecast_dynamics is not None,
        "locations": list(locations),
        "quantile_levels": [float(q) for q in result.quantile_levels],
        "reference_dates": [str(d) for d in result.reference_dates],
        "parameters": list(result.param_names),
        **(run_info or {}),
    }
    (output_folder / "run.json").write_text(json.dumps(info, indent=2, default=str))
    return output_folder
