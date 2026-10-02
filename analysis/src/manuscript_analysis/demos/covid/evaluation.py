"""Loading, scoring and the manuscript figures for Demo 2.

The counterpart to `demo-flu/evaluation.py`, and deliberately parallel to it: imported by
both `evaluation.ipynb` and `export.py`, so a figure in the paper and
the same figure in the notebook come from one function.

Three ways this differs from Demo 1, all because Demo 2 is shaped differently:

1. **Two quantities that do not add.** A hospital census is a stock and deaths are a flow,
   so there is no `total` row and every score is per quantity.
2. **Three scored locations, not 51.** There is no distribution across jurisdictions to
   plot, so nothing here corresponds to Demo 1's Figure 2(d) swarm.
3. **The forecast and the fit live at different scales.** County models forecast at 3
   states (summed within each realization) but fit at their own 32 counties. Quantiles do
   not add, so a county fit can never be shown at the state scale; see `figure_fit`.

Figure numbering follows `drafts/figure-plan-v01.md`, where this is Figure 3.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from manuscript_analysis.demos import paths
from manuscript_analysis.demos.lib.figures import (
    AUTO_TITLE,
    DOUBLE_COLUMN,
    ONE_AND_HALF_COLUMN,
    resolve_title,
)
from manuscript_analysis.demos.lib.plots import (
    panel_grid,
    plot_flow_matrix,
    plot_line_panels,
    plot_quantile_grid,
    plot_ratio_swarm,
    plot_rolling_forecast_grid,
)
from manuscript_analysis.demos.lib.results import (
    align_observations,
    load_observations,
    load_run,
    load_runs,
    quantile_array,
)
from manuscript_analysis.demos.lib.scoring import (
    DEMO_QUANTILE_LEVELS,
    HEADLINE_SCALE,
    SCORE_LABELS,
    SCALES,
    check_scale,
    interval_coverage,
    relative_wis,
    weighted_interval_score,
)

from .models import covid_season

__all__ = [
    "BASELINE",
    "COLORS",
    "CORRELATED_MODELS",
    "Evaluation",
    "correlated_county_table",
    "correlated_table",
    "county_relative",
    "county_scores",
    "figure_calibration",
    "figure_county_relative_wis",
    "figure_fit",
    "figure_movement_structure",
    "figure_parameter_correlation",
    "figure_relative_wis",
    "figure_rolling_forecasts",
    "figure_wis_by_horizon",
    "focus_counties",
    "load",
    "load_correlated",
    "load_replicate",
    "node_forecasts",
    "relative_by_unit",
    "relative_pooled",
    "wis_by_location",
    "wis_table",
]

MODELS = ("movement", "county", "state")
BASELINE = "state"

# The same paper-wide mapping as Demo 1, and it lines the two demos up deliberately:
# the baseline has no added structure (grey), one model adds structure *and* the data that
# drives it (blue), and one adds the structure with the data deliberately removed (orange).
#
#   Demo 1: empirical mixing / homogeneous mixing / no age structure
#   Demo 2: counties + commuting / counties, no movement / no spatial structure
#
# `county` is the degraded middle: it has the spatial resolution but no movement between
# nodes, exactly as homogeneous mixing has the age strata but no measured contact matrix.
COLORS = {
    "movement": "tab:blue",
    "county": "tab:orange",
    "state": "tab:grey",
}
LABELS = {
    "movement": "counties + commuting",
    "county": "counties, no movement",
    "state": "no spatial structure",
}

CORRELATED_MODELS = (
    "county-correlated",
    "county-correlated-strong",
    "movement-correlated",
    "movement-correlated-strong",
)
"""The correlated-OU sensitivity analysis: the two county models with their counties'
parameter shocks correlated in space. Not part of the main comparison, so not in `MODELS`;
see `covid_season.CORRELATION_FITTED` and `CORRELATION_STRONG`."""

UNCORRELATED = {
    "county-correlated": "county",
    "county-correlated-strong": "county",
    "movement-correlated": "movement",
    "movement-correlated-strong": "movement",
}
"""Each correlated model's twin: the same model with independent county shocks."""

QUANTITIES = ("census", "deaths")
QUANTITY_LABELS = {
    "census": "hospital census (mean weekly inpatients)",
    "deaths": "weekly deaths",
}
AXIS_LABELS = {
    "census": "hospital census",
    "deaths": "weekly deaths",
}
"""The short form, for a y axis or a swarm row. The long form does not fit beside a
1.8-inch panel row and is clipped there; use it in a caption or a table instead.

Change the wording here and every figure follows: nothing downstream spells an axis
label out. "Deaths" rather than "mortalities" deliberately: it is the term the CDC
source and the epidemiological literature use for a count, and "mortality" normally
denotes a rate. It also parallels Demo 1's "weekly admissions"."""
DIMS = ["reference_date", "horizon", "location"]

REPLICATE_SEED = 1
"""The seed-1 replicate. Both demos now name run folders for the model at every seed, so
loading a replicate is a different seed and nothing else."""


class Evaluation(NamedTuple):
    """Everything the figures need, loaded and scored once."""

    runs: dict
    observations: pd.DataFrame
    """County-level, as frozen. `state_observations` is what scoring joins against."""
    state_observations: pd.DataFrame
    forecasts: dict[str, np.ndarray]
    """Per model, `(origins, horizons, locations, quantities, levels)`."""
    observed: np.ndarray
    """`(origins, horizons, locations, quantities)`; identical for every model, checked."""
    scores: dict[str, dict[str, object]]
    """`scores[model][quantity]`. There is no pooled score across quantities: a census
    and a death count are not commensurate, so adding their WIS would be meaningless."""
    scale: str
    """What `scores` are computed on: `"log"` (the manuscript's) or `"natural"`."""
    coverage: dict
    """`coverage[nominal][model][quantity]`."""
    origins: np.ndarray
    horizons: np.ndarray
    locations: np.ndarray
    """State FIPS codes, in the order of the array axes."""
    labels: dict[str, str]
    """Node code to display name, covering both scales: a state FIPS gives its postal
    abbreviation, a county FIPS its name. Figures title panels with
    `labels.get(node, node)`, so a code that is in neither still draws."""


def _node_labels() -> dict[str, str]:
    """Display names for every node either scale can ask about.

    Both are needed because Demo 2's figures are drawn at two scales: the scored states
    and, for the county models, their own 32 counties.
    """
    states = covid_season.state_scope()
    counties = covid_season.scope()
    return {
        **dict(zip(states.node_ids, states.labels)),
        **dict(zip(counties.node_ids, counties.labels)),
    }


def _harmonize_dates(observations: pd.DataFrame) -> pd.DataFrame:
    """Relabel every quantity onto one week convention, the first quantity's.

    **The two quantities label the same MMWR week at opposite ends.** The hospital census
    is dated by the week's starting Sunday and deaths by its ending Saturday, six days
    later, which is why `Season.start_date` must be a Sunday in the first place. The
    forecast files label every week from the *first* quantity, because that is what
    `run_rolling_origin` reads out of the source array, so deaths would join nothing at
    all and scoring would fail outright rather than quietly mis-score.

    Weeks are matched by position, not by arithmetic on a fixed offset: both quantities
    cover the same ordered set of MMWR weeks, so the i-th of one is the i-th of the other
    whatever the labelling convention happens to be.
    """
    per_quantity = {
        quantity: np.sort(part["date"].unique())
        for quantity, part in observations.groupby("quantity")
    }
    reference = per_quantity[QUANTITIES[0]]
    sizes = {q: len(d) for q, d in per_quantity.items()}
    if len(set(sizes.values())) != 1:
        raise ValueError(f"quantities cover different numbers of weeks: {sizes}")

    relabelled = observations.copy()
    for quantity, dates in per_quantity.items():
        if quantity == QUANTITIES[0]:
            continue
        mapping = dict(zip(dates, reference))
        rows = relabelled["quantity"] == quantity
        relabelled.loc[rows, "date"] = relabelled.loc[rows, "date"].map(mapping)
    return relabelled


def _to_state_observations(observations: pd.DataFrame) -> pd.DataFrame:
    """Sum the county observations to the states the comparison is scored at.

    Both quantities sum across *nodes*: a state's census is the total inpatients in its
    counties, and its deaths are their total deaths. That is not in tension with the
    census being a weekly *mean* over time; the two axes aggregate differently, which is
    the same distinction `manuscript_analysis.demos.lib.forecasting.Quantity` encodes.
    """
    grouped = _harmonize_dates(observations)
    grouped["location"] = grouped["location"].str[:2]
    return (
        grouped.groupby(["date", "location", "quantity"], as_index=False)["value"].sum()
    )


def load(
    output_root: str | Path | None = None,
    models: Sequence[str] = MODELS,
    levels: Sequence[float] = DEMO_QUANTILE_LEVELS,
    observations_csv: str | Path | None = None,
    scale: str = HEADLINE_SCALE,
    extra_runs: Mapping[str, str | Path] | None = None,
) -> Evaluation:
    """Load every model's output, align it to the observations, and score it.

    `extra_runs` maps further model names to their own run folders, for runs that live
    outside `output_root`, such as the correlated-OU sensitivity runs. They are scored
    exactly like `models`, against the same target.

    `scale` names the scale the scores are computed on: `"log"`, the default and what
    the manuscript reports, transforms observations and forecasts by `log(x + 1)` before
    scoring; `"natural"` scores the counts as they are. Coverage is the same either way.

    `observations_csv` defaults to `observations.csv` beside the runs. The replicate tree
    has none of its own: both seeds are scored against the one frozen file, which is the
    whole point of freezing it, and here it matters more than in Demo 1 because the
    suppressed-death imputation is a random draw.
    """
    transform = check_scale(scale)
    output_root = Path(output_root or paths.runs("covid", seed=0))
    runs = load_runs(output_root, list(models))
    for name, folder in (extra_runs or {}).items():
        runs[name] = load_run(folder)
    models = list(runs)

    observations = _harmonize_dates(load_observations(
        observations_csv or paths.observations("covid")
    ))
    state_observations = _to_state_observations(observations)

    forecasts, observed_each, coords = {}, {}, {}
    for name, run in runs.items():
        frame = run.forecasts
        # Runs written before the `scale` column carry only the scored resolution.
        if "scale" in frame.columns:
            frame = frame[frame["scale"] == "scored"]
        per_quantity, per_quantity_observed = [], []
        for quantity in QUANTITIES:
            part = frame[frame["quantity"] == quantity]
            values, coords[name] = quantile_array(part, DIMS, levels=levels)
            per_quantity.append(values)
            per_quantity_observed.append(
                align_observations(
                    part, DIMS, state_observations, quantity=quantity
                )
            )
        # (origins, horizons, locations, quantities, levels)
        forecasts[name] = np.stack(per_quantity, axis=3)
        observed_each[name] = np.stack(per_quantity_observed, axis=3)

    reference = observed_each[models[0]]
    for name in models[1:]:
        if not np.array_equal(observed_each[name], reference):
            raise ValueError(f"{name} was scored against different observations")

    scores, coverage = {}, {0.95: {}, 0.50: {}}
    for name in models:
        scores[name] = {
            quantity: weighted_interval_score(
                reference[..., i], forecasts[name][..., i, :], levels, transform
            )
            for i, quantity in enumerate(QUANTITIES)
        }
        for nominal in (0.95, 0.50):
            coverage[nominal][name] = {
                quantity: interval_coverage(
                    reference[..., i], forecasts[name][..., i, :], levels,
                    nominal=nominal,
                )
                for i, quantity in enumerate(QUANTITIES)
            }

    first = coords[models[0]]
    return Evaluation(
        runs=runs,
        observations=observations,
        state_observations=state_observations,
        forecasts=forecasts,
        observed=reference,
        scores=scores,
        scale=scale,
        coverage=coverage,
        origins=first["reference_date"],
        horizons=first["horizon"],
        locations=first["location"],
        labels=_node_labels(),
    )


def load_replicate(
    models: Sequence[str] = MODELS,
    levels: Sequence[float] = DEMO_QUANTILE_LEVELS,
    scale: str = HEADLINE_SCALE,
) -> Evaluation:
    """The seed-1 replicate, scored identically against the same frozen observations.

    All three models at seed 1, never a seed-1 model against the seed-0 baseline: the
    denominator has to be built exactly like the numerator, and two earlier Demo 2
    analyses were wrong in precisely that way.
    """
    return load(
        output_root=paths.runs("covid", seed=REPLICATE_SEED),
        models=models,
        levels=levels,
        scale=scale,
    )


def load_correlated(
    seed: int = 0,
    models: Sequence[str] = CORRELATED_MODELS,
    scale: str = HEADLINE_SCALE,
) -> Evaluation:
    """The main three models plus whichever correlated-OU runs exist, at one seed.

    Loaded in one `Evaluation` so every model is scored against the same target, and so
    a correlated model can be compared with its uncorrelated twin. A run that has not
    finished is left out rather than raising, so this can be read while runs are going.
    """
    root = paths.correlated_runs("covid", seed=seed)
    present = {
        name: root / name for name in models if (root / name / "run.json").exists()
    }
    return load(
        output_root=paths.runs("covid", seed=seed),
        models=MODELS,
        scale=scale,
        extra_runs=present,
    )


def correlated_table(
    ev: Evaluation, levels: Sequence[float] = DEMO_QUANTILE_LEVELS
) -> pd.DataFrame:
    """The sensitivity analysis at the scored (state) scale, every loaded model.

    `rel uncorrelated` compares a correlated model with its twin. `median / observed` is
    the sum of forecast medians over the sum of observations at the longest horizon,
    where the county models' upward drift was largest; coverage is given there too.
    """
    label = SCORE_LABELS[ev.scale]
    median = list(levels).index(0.5)
    last = len(ev.horizons) - 1
    rows = []
    for quantity in QUANTITIES:
        q = QUANTITIES.index(quantity)
        observed = ev.observed[:, last, :, q]
        for model in ev.forecasts:
            twin = UNCORRELATED.get(model)
            medians = ev.forecasts[model][:, last, :, q, median]
            rows.append({
                "quantity": quantity,
                "model": model,
                label: ev.scores[model][quantity].total.mean(),
                f"rel {label}": relative_pooled(ev, model, quantity),
                "rel uncorrelated": (
                    relative_pooled(ev, model, quantity, against=twin)
                    if twin else np.nan
                ),
                "cov50": ev.coverage[0.50][model][quantity].mean(),
                "cov95": ev.coverage[0.95][model][quantity].mean(),
                f"cov95 h{ev.horizons[last]}":
                    ev.coverage[0.95][model][quantity][:, last].mean(),
                f"median / observed h{ev.horizons[last]}":
                    medians.sum() / observed.sum(),
            })
    return pd.DataFrame(rows).set_index(["quantity", "model"])


def correlated_county_table(
    ev: Evaluation, levels: Sequence[float] = DEMO_QUANTILE_LEVELS
) -> pd.DataFrame:
    """The same models at their own 32 counties: the sanity check on the design.

    Correlating the shocks leaves each county's own process unchanged, so without
    movement a county's forecast should be statistically unchanged and `rel uncorrelated`
    should sit near 1. Only the state sums should move.
    """
    label = SCORE_LABELS[ev.scale]
    transform = SCALES[ev.scale]
    rows = []
    for quantity in QUANTITIES:
        for model in ev.forecasts:
            if model == BASELINE:
                continue
            frame = node_forecasts(ev, model)
            frame = frame[frame["quantity"] == quantity]
            values, _ = quantile_array(frame, DIMS, levels=levels)
            observed = align_observations(frame, DIMS, ev.observations, quantity=quantity)
            scores = weighted_interval_score(observed, values, levels, transform).total
            twin = UNCORRELATED.get(model)
            rows.append({
                "quantity": quantity,
                "model": model,
                label: scores.mean(),
                "rel uncorrelated": (
                    float(relative_wis(scores, county_scores(ev, twin, quantity)[0]))
                    if twin else np.nan
                ),
                "cov95": np.nanmean(
                    interval_coverage(observed, values, levels, nominal=0.95)
                ),
            })
    return pd.DataFrame(rows).set_index(["quantity", "model"])


def wis_table(ev: Evaluation) -> pd.DataFrame:
    """Mean WIS per model per quantity, with relative WIS against the baseline.

    Columns are named for the scale, `WIS` or `log WIS`. The scores are arithmetic means;
    the relative column is the ratio of geometric means (`relative_wis`), so it is not
    simply one mean divided by another.
    """
    label = SCORE_LABELS[ev.scale]
    rows = []
    for model in MODELS:
        for quantity in QUANTITIES:
            rows.append({
                "model": model,
                "quantity": quantity,
                label: ev.scores[model][quantity].total.mean(),
                f"rel {label}": relative_pooled(ev, model, quantity),
                "cov95": ev.coverage[0.95][model][quantity].mean(),
                "cov50": ev.coverage[0.50][model][quantity].mean(),
            })
    return pd.DataFrame(rows).set_index(["model", "quantity"])


def relative_pooled(
    ev: Evaluation, model: str, quantity: str, against: str = BASELINE
) -> float:
    """Relative WIS of `model` against `against`, pooled over origins, horizons and states.

    The ratio of geometric means (`relative_wis`), on `ev.scale`. Below 1 means `model`
    is better.
    """
    return float(relative_wis(
        ev.scores[model][quantity].total, ev.scores[against][quantity].total
    ))


def relative_by_unit(
    ev: Evaluation, model: str, quantity: str, against: str = BASELINE
) -> np.ndarray:
    """Per-state relative WIS against the baseline; below 1 means `model` is better.

    The ratio of geometric means over origins and horizons, on `ev.scale`. Same name and
    meaning as Demo 1's, with a `quantity` argument because Demo 2 scores two channels
    that are not commensurate. `against="county"` gives the movement contrast. Demo 2's
    finer units are counties; see `county_relative`.
    """
    return relative_wis(
        ev.scores[model][quantity].total,
        ev.scores[against][quantity].total,
        axis=(0, 1),
    )


def wis_by_location(ev: Evaluation) -> pd.DataFrame:
    """Mean WIS per state, per model, per quantity, with ratios. For the supplement.

    The model columns are arithmetic means on `ev.scale`; the ratio columns are relative
    WIS, the ratio of geometric means.

    The index column is `jurisdiction`, not `state`: one of the models is *named* `state`,
    and a column named for both a label and a model silently overwrites one with the other.
    """
    rows = []
    for i, code in enumerate(ev.locations):
        for quantity in QUANTITIES:
            row = {"jurisdiction": ev.labels[code], "quantity": quantity}
            for model in MODELS:
                row[model] = ev.scores[model][quantity].total.mean(axis=(0, 1))[i]
            for model in MODELS:
                if model != BASELINE:
                    row[f"{model} / {BASELINE}"] = relative_by_unit(
                        ev, model, quantity
                    )[i]
            # The informative contrast for the movement question: same resolution,
            # movement on against movement off.
            row["movement / county"] = relative_by_unit(
                ev, "movement", quantity, against="county"
            )[i]
            rows.append(row)
    return pd.DataFrame(rows).set_index(["jurisdiction", "quantity"])


def focus_counties() -> list[str]:
    """The largest county in each scored state, by population.

    Which counties the county-resolved panels show. Largest rather than a fixed list
    because a small county sits near zero for most of the season and shows nothing; the
    choice is not load-bearing, and every county is scored whatever this returns.

    Lives here rather than in the notebook because the figures, the notebook and
    `export_manuscript.py` all need the same three, and three copies of a loop is three
    chances to show different counties in the paper and in the notebook.
    """
    population = covid_season.population()
    counties = list(covid_season.scope().node_ids)
    largest = []
    for state in covid_season.state_scope().node_ids:
        best, best_population = None, -1.0
        for index, code in enumerate(counties):
            if code.startswith(state) and population[index] > best_population:
                best, best_population = code, population[index]
        largest.append(best)
    return largest


def figure_fit(
    ev: Evaluation,
    model: str,
    locations: Sequence[str] | None = None,
    quantities: Sequence[str] = QUANTITIES,
    series: str = "prior",
    levels=DEMO_QUANTILE_LEVELS,
    max_panels: int = 3,
    title: str | None = AUTO_TITLE,
    subfig=None,
    color: str | None = None,
):
    """The weekly fit against observations: one row per quantity, one column per node.

    Serves two panels of Figure 3, because they differ only in which nodes are passed:

    - **(b)**, the state model at its 3 states.
    - **the county panel**, any subset of a county model's 32 counties. This is the
      counterpart to Demo 1's age-resolved panel: Demo 1 resolves the fit by age band,
      Demo 2 resolves it by county, and both show the model fitting many channels rather
      than one. Both are drawn by `manuscript_analysis.demos.lib.plots.plot_quantile_grid`.

    Always shown at the **model's own nodes**. A county fit can never be redrawn at the
    state scale: the fit is stored as quantiles, and quantiles do not add. Only the
    forecast is aggregated, inside each realization before quantiling.

    `series` defaults to **prior**, the one-week-ahead prediction taken before the Kalman
    update, because that is a genuine prediction; the posterior is pulled onto the
    observation by construction and always looks good.

    `title` takes a string, or None to draw none; see `manuscript_analysis.demos.lib.figures.resolve_title`.
    """
    if series not in ("prior", "posterior"):
        raise ValueError(f"series must be 'prior' or 'posterior', got {series!r}")
    bad = [q for q in quantities if q not in QUANTITIES]
    if bad:
        raise ValueError(f"unknown quantities {bad}; this demo observes {QUANTITIES}")

    fit = ev.runs[model].fit
    fit = fit[fit["series"] == series]
    available = list(dict.fromkeys(fit["location"]))
    nodes = list(locations) if locations is not None else available[:max_panels]
    missing = [n for n in nodes if n not in available]
    if missing:
        raise ValueError(
            f"{model} has no fit for {missing}; it runs on "
            f"{len(available)} nodes such as {available[:3]}"
        )

    rows = []
    for row, quantity in enumerate(quantities):
        # Per-quantity observations: county nodes join the frozen county table, state
        # nodes the summed one. A 2-character FIPS is a state.
        panels = []
        for node in nodes:
            part = fit[(fit["location"] == node) & (fit["quantity"] == quantity)]
            values, coords = quantile_array(part, ["target_end_date"], levels=levels)
            dates = pd.to_datetime(coords["target_end_date"])
            table = ev.state_observations if len(node) == 2 else ev.observations
            seen = table[
                (table["quantity"] == quantity)
                & (table["location"] == node)
                & (pd.to_datetime(table["date"]).isin(dates))
            ].sort_values("date")
            panels.append({
                "dates": dates,
                "quantiles": {q: values[:, i] for i, q in enumerate(levels)},
                "observed": (seen["date"].to_numpy(), seen["value"].to_numpy()),
                "color": color or COLORS[model],
                # Only the top row is titled: every column is the same node throughout.
                "title": ev.labels.get(node, node) if row == 0 else None,
            })
        rows.append(panels)

    # BARS, matching Demo 1: consecutive weeks of a filter's fit are separate
    # predictions, each issued from a freshly corrected state, so joining them into a
    # ribbon implies a continuity between them that does not exist. The forecast fans
    # are bands, because each fan IS one trajectory.
    fig, _ = plot_quantile_grid(
        rows,
        style="bars",
        ylabels=[AXIS_LABELS[q] for q in quantities],
        title=resolve_title(title, f"{LABELS[model]}: {series} fit"),
        figure_width=DOUBLE_COLUMN,
        panel_height=1.8,
        subfig=subfig,
    )
    return fig


def figure_rolling_forecasts(
    ev: Evaluation,
    model: str,
    locations: Sequence[str] | None = None,
    quantities: Sequence[str] = QUANTITIES,
    levels=DEMO_QUANTILE_LEVELS,
    title: str | None = AUTO_TITLE,
    subfig=None,
    color: str | None = None,
):
    """Every origin's forecast fan against the observed series.

    One row per quantity, one column per node, at either of two scales:

    - **scored**, the default: the 3 states every model is compared at, read from
      `ev.forecasts`. The county models' 32-county ensembles are summed to 3 states
      inside each realization before quantiling, so this is the panel that corresponds
      to the WIS tables.
    - **the model's own nodes**, by passing county FIPS codes. Those come from the
      per-node forecast rows (see `node_forecasts`), written only by runs that carry the
      `scale` column, and are scored against the frozen county observations rather than
      the state sums.

    The county scale is the one where movement can show up at all: summing 32 partly
    independent nodes cancels exactly the noise the movement model represents. It is
    Demo 2's counterpart to Demo 1's `figure_rolling_forecasts_by_age`, which resolves
    the same figure by age band instead of by county, and both draw their panels with
    `manuscript_analysis.demos.lib.plots.plot_rolling_forecast_grid`.

    Panel arguments match `figure_fit`, so the filter fit and the forecasts for one set
    of counties can be asked for the same way.
    """
    bad = [q for q in quantities if q not in QUANTITIES]
    if bad:
        raise ValueError(f"unknown quantities {bad}; this demo observes {QUANTITIES}")

    scored = list(ev.locations)
    nodes = list(locations) if locations is not None else scored
    if not nodes:
        raise ValueError("no locations to draw")

    # One scale per figure: the two have different observations and different y scales,
    # so mixing a state panel with a county panel would silently compare unlike things.
    if all(node in scored for node in nodes):
        frame = None
    else:
        frame = node_forecasts(ev, model)
        available = list(dict.fromkeys(frame["location"]))
        missing = [node for node in nodes if node not in available]
        if missing:
            raise ValueError(
                f"{model} forecasts neither the scored states {scored} nor {missing}; "
                f"it runs on {len(available)} nodes such as {available[:3]}"
            )

    index = {q: i for i, q in enumerate(QUANTITIES)}
    rows = []
    for row, quantity in enumerate(quantities):
        panels = []
        for node in nodes:
            if frame is None:
                origins, horizons = ev.origins, ev.horizons
                values = ev.forecasts[model][:, :, scored.index(node),
                                             index[quantity], :]
            else:
                part = frame[
                    (frame["location"] == node) & (frame["quantity"] == quantity)
                ]
                values, coords = quantile_array(
                    part, ["reference_date", "horizon"], levels=levels
                )
                origins, horizons = coords["reference_date"], coords["horizon"]
            # A 2-character FIPS is a state, so it joins the summed table; a 5-character
            # one is a county and joins the frozen county table. Same test as `figure_fit`.
            table = ev.state_observations if len(node) == 2 else ev.observations
            seen = table[
                (table["quantity"] == quantity) & (table["location"] == node)
            ].sort_values("date")
            panels.append({
                "origins": origins,
                "horizons": horizons,
                "values": values,
                "observed": (seen["date"].to_numpy(), seen["value"].to_numpy()),
                "color": color or COLORS[model],
                "title": ev.labels.get(node, node) if row == 0 else None,
            })
        rows.append(panels)

    scale = "" if frame is None else f", {len(nodes)} of its own nodes"
    fig, _ = plot_rolling_forecast_grid(
        rows,
        levels,
        ylabels=[AXIS_LABELS[q] for q in quantities],
        title=resolve_title(title, f"Rolling forecasts, {LABELS[model]}{scale}"),
        figure_width=DOUBLE_COLUMN,
        panel_height=1.8,
        subfig=subfig,
    )
    return fig


def figure_wis_by_horizon(
    ev: Evaluation,
    title: str | None = None,
    subfig=None,
    legend: bool | str = True,
):
    """Figure 3(c): skill against horizon, one panel per quantity, three models each.

    Two panels where Demo 1 has one, because Demo 2 fits a stock and a flow jointly under
    one likelihood and the two can disagree. That asymmetry shows an epymorph capability
    rather than papering over a gap. Same helper as Demo 1's
    (`manuscript_analysis.demos.lib.plots.plot_line_panels`), so the two demos' skill curves match.

    `share_y` is off: a census WIS and a deaths WIS are not commensurate, and putting
    them on one scale would make the smaller one unreadable.
    """
    series = {
        LABELS[model]: np.stack([
            ev.scores[model][quantity].total.mean(axis=(0, 2))
            for quantity in QUANTITIES
        ])
        for model in MODELS
    }
    fig, _ = plot_line_panels(
        ev.horizons,
        series,
        colors={LABELS[model]: COLORS[model] for model in MODELS},
        titles=[AXIS_LABELS[q] for q in QUANTITIES],
        ylabel=SCORE_LABELS[ev.scale],
        xlabel="horizon (weeks ahead)",
        xticks=ev.horizons,
        suptitle=title,
        legend=legend,
        legend_loc="upper left",
        figure_width=DOUBLE_COLUMN,
        panel_height=2.3,
        share_y=False,
        subfig=subfig,
    )
    return fig


def figure_relative_wis(
    ev: Evaluation,
    replicate: Evaluation | None = None,
    title: str | None = None,
    subfig=None,
):
    """Figure 3(d): per-state WIS ratio against the baseline, by quantity.

    Grouped bars rather than Demo 1's swarm: with three states there is no distribution
    to show, and naming all three is honest here in a way naming 51 was not. Each bar
    carries a marker per seed when a replicate is passed, for the same reason Demo 1's
    figure shows both seeds: with two replicates, draw the replicates.
    """
    structured = [m for m in MODELS if m != BASELINE]
    fig, axs = panel_grid(
        1, len(QUANTITIES), subfig=subfig,
        figsize=(DOUBLE_COLUMN, 2.4), sharey=True,
    )
    axs = axs[0]
    width = 0.8 / len(structured)
    positions = np.arange(len(ev.locations))

    for quantity, ax in zip(QUANTITIES, axs):
        for offset, model in enumerate(structured):
            x = positions + (offset - (len(structured) - 1) / 2) * width
            ratios = relative_by_unit(ev, model, quantity)
            ax.bar(x, ratios, width=width * 0.9, color=COLORS[model],
                   label=LABELS[model])
            if replicate is not None:
                other = relative_by_unit(replicate, model, quantity)
                ax.scatter(x, other, s=10, facecolor="white",
                           edgecolor="black", linewidth=0.6, zorder=3)
        ax.axhline(1.0, color="black", linewidth=0.8)
        ax.set_xticks(positions)
        ax.set_xticklabels([ev.labels[c] for c in ev.locations])
        ax.set_title(AXIS_LABELS[quantity], fontsize=7)
    axs[0].set_ylabel(f"{SCORE_LABELS[ev.scale]} relative to\n{LABELS[BASELINE]}")
    axs[0].legend(fontsize=6)
    if replicate is not None:
        axs[-1].set_xlabel("open marker: seed 1", fontsize=6)
    if title is not None:
        fig.suptitle(title)
    return fig


def figure_calibration(
    ev: Evaluation,
    nominal: float = 0.95,
    title: str | None = None,
    subfig=None,
    legend: bool | str = True,
):
    """Interval coverage against nominal, one line per model, one panel per quantity.

    Demo 2's half of the supplementary calibration figure (`export_manuscript`), and
    the counterpart to Demo 1's `figure_calibration`: same helper, same encoding, two panels instead of one. The two
    spatial scales are expected to miss in opposite directions, which is the
    methodological point: WIS is an awkward adjudicator between forecasts at different
    spatial scales, because aggregating partly-independent nodes cancels noise that a
    single node retains.
    """
    series = {
        LABELS[model]: np.stack([
            np.array([
                ev.coverage[nominal][model][quantity][:, i].mean()
                for i in range(len(ev.horizons))
            ])
            for quantity in QUANTITIES
        ])
        for model in MODELS
    }
    fig, _ = plot_line_panels(
        ev.horizons,
        series,
        colors={LABELS[model]: COLORS[model] for model in MODELS},
        titles=[AXIS_LABELS[q] for q in QUANTITIES],
        ylabel=f"{nominal:.0%} interval coverage",
        xlabel="horizon (weeks ahead)",
        xticks=ev.horizons,
        ylim=(0, 1),
        reference=nominal,
        reference_label="nominal",
        suptitle=title,
        legend=legend,
        figure_width=DOUBLE_COLUMN,
        panel_height=2.3,
        subfig=subfig,
    )
    return fig


def figure_movement_structure(
    ax=None,
    title: str | None = AUTO_TITLE,
    subfig=None,
):
    """Figure 3(a): the commuting matrix, which is what varies between the models.

    **One matrix, three models.** This single panel is the whole experimental design, and
    that is why it is worth a main-text panel rather than a supplementary one:

    - `movement` uses the matrix as drawn, off-diagonal flows and all.
    - `county` keeps the same 32 nodes but uses **only the diagonal**: people stay home.
    - `state` collapses each white-bordered block to a single node.

    So the three models are three readings of one picture, exactly as Demo 1's three models
    are three readings of one contact matrix. Drawing it as the opening panel is what makes
    the parallel between the demos visible rather than something a reader has to infer.

    Log scale, because the diagonal runs two to three orders of magnitude above the
    off-diagonal and on a linear scale the off-diagonal structure vanishes.

    Takes `subfig` like every other panel function, or `ax` to draw onto axes the caller
    already has. The colorbar is attached to whichever figure it lands in.

    The default title is the share of workers who cross a county line, which is the one
    number that says whether movement can matter at all here. Pass `title=None` to drop
    it, or a string of your own; see `manuscript_analysis.demos.lib.figures.resolve_title`.
    """
    commuters = covid_season.commuters()
    counties = list(covid_season.scope().node_ids)
    groups = np.array([county[:2] for county in counties])
    labels = [
        covid_season.state_scope().labels[i]
        for i in range(covid_season.state_scope().nodes)
    ]

    # Three ways in, because this panel is drawn standalone, into a composed figure,
    # and (historically) onto an axes someone else made.
    if ax is not None:
        fig = ax.figure
    elif subfig is not None:
        fig = subfig
        ax = fig.subplots(1, 1)
    else:
        fig, ax = plt.subplots(
            figsize=(DOUBLE_COLUMN / 2, 3.2), layout="constrained"
        )

    image = plot_flow_matrix(
        ax, commuters, groups, group_labels=labels,
        xlabel="work county", ylabel="home county",
    )
    bar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.03)
    bar.set_label("commuters per week (log$_{10}$)", fontsize=6)
    bar.ax.tick_params(labelsize=5)
    ax.set_xticks([])
    ax.set_yticks([])

    crossing = commuters.sum() - np.trace(commuters)
    heading = resolve_title(
        title, f"{crossing / commuters.sum():.0%} of workers cross a county line"
    )
    if heading is not None:
        ax.set_title(heading, fontsize=7)
    return fig
def figure_parameter_correlation(
    parameter: str = "log_beta",
    title: str | None = AUTO_TITLE,
    subfig=None,
):
    """The county-by-county correlation of one parameter's daily shocks, both settings.

    Drawn like `figure_movement_structure`, with counties grouped by state, so the two
    can be read side by side: commuting is what couples the counties in `movement`, and
    this is what couples their parameters in the correlated models.
    """
    settings = {
        "fitted": covid_season.CORRELATION_FITTED,
        "strong": covid_season.CORRELATION_STRONG,
    }
    counties = list(covid_season.scope().node_ids)
    groups = np.array([county[:2] for county in counties])
    labels = [
        covid_season.state_scope().labels[i]
        for i in range(covid_season.state_scope().nodes)
    ]

    if subfig is not None:
        fig = subfig
        axs = fig.subplots(1, 2)
    else:
        fig, axs = plt.subplots(1, 2, figsize=(DOUBLE_COLUMN, 3.0), layout="constrained")

    pairs = np.triu_indices(len(counties), 1)
    for ax, (name, setting) in zip(axs, settings.items()):
        factor = covid_season.parameter_cholesky(setting)[parameter]
        correlation = factor @ factor.T
        image = plot_flow_matrix(
            ax, correlation, groups, group_labels=labels, log=False,
            xlabel="county", ylabel="county",
        )
        image.set_clim(0, 1)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(
            f"{name}: mean pair correlation {correlation[pairs].mean():.2f}", fontsize=7
        )
    bar = fig.colorbar(image, ax=axs, fraction=0.046, pad=0.03)
    bar.set_label(f"correlation of daily {parameter} shocks", fontsize=6)
    bar.ax.tick_params(labelsize=5)

    heading = resolve_title(
        title,
        f"exp(-d / {covid_season.CORRELATION_FITTED.length_scale:g} mi), "
        "with and without a county-local share",
    )
    if heading is not None:
        fig.suptitle(heading, fontsize=8)
    return fig


def node_forecasts(ev: Evaluation, model: str) -> pd.DataFrame:
    """The per-node forecast rows for `model`, at its own nodes rather than the scored ones.

    Present only in runs written with the `scale` column and only for models whose
    geography is coarsened for scoring: without grouping, the scored nodes already are the
    model's nodes and `ev.forecasts` is what you want.
    """
    frame = ev.runs[model].forecasts
    if "scale" not in frame.columns:
        raise ValueError(
            f"{model} was run before per-node forecasts were written; re-run it to get "
            "county-resolved forecasts"
        )
    nodes = frame[frame["scale"] == "model"]
    if nodes.empty:
        raise ValueError(
            f"{model} writes no model-scale forecasts; it is not scored at a coarser "
            "geography than it runs at"
        )
    return nodes


def county_scores(ev: Evaluation, model: str, quantity: str, levels=DEMO_QUANTILE_LEVELS):
    """WIS per county for one model, from the model-scale forecasts.

    Available only for runs written with the `scale` column; see `node_forecasts`. Scored
    against the frozen **county** observations, not the state sums, so this is a genuine
    per-county comparison rather than a decomposition of the state-scale result. Scored
    on `ev.scale`, so a county score is always on the same scale as the state scores.
    """
    frame = node_forecasts(ev, model)
    frame = frame[frame["quantity"] == quantity]
    values, coords = quantile_array(frame, DIMS, levels=levels)
    observed = align_observations(frame, DIMS, ev.observations, quantity=quantity)
    transform = SCALES[ev.scale]
    return (
        weighted_interval_score(observed, values, levels, transform).total,
        coords["location"],
    )


def county_relative(ev: Evaluation, quantity: str) -> tuple[np.ndarray, np.ndarray]:
    """Per-county relative WIS, movement against no movement, and the county codes.

    The `state` model has no county-scale forecast to compare against, so this contrast
    is necessarily `movement / county`: same 32 nodes, same everything, movement on
    against movement off. The ratio of geometric means over origins and horizons; the
    few county-weeks where either model scores exactly zero are dropped from both, as
    `relative_wis` explains.
    """
    numerator, locations = county_scores(ev, "movement", quantity)
    denominator, _ = county_scores(ev, "county", quantity)
    return relative_wis(numerator, denominator, axis=(0, 1)), locations


def figure_county_relative_wis(
    ev: Evaluation,
    replicate: Evaluation | None = None,
    quantities: Sequence[str] = QUANTITIES,
    title: str | None = AUTO_TITLE,
    subfig=None,
):
    """Per-county WIS ratio, movement against no movement, one row per quantity.

    Demo 2's counterpart to Demo 1's Figure 2(d), and the only Demo 2 panel with enough
    units for a distribution: 32 counties rather than 3 states. The contrast is movement
    on against movement off at identical spatial resolution, which is the cleanest form of
    the movement question.

    Drawn at the **county** scale deliberately. The state-scale comparison pools 32
    partly-independent nodes, which cancels exactly the noise the movement model is trying
    to represent; this is the scale at which movement can actually show up.
    """
    rows = []
    for quantity in quantities:
        seeds = [county_relative(ev, quantity)[0]]
        if replicate is not None:
            seeds.append(county_relative(replicate, quantity)[0])
        rows.append({
            "label": AXIS_LABELS[quantity],
            "color": COLORS["movement"],
            "seeds": seeds,
        })

    fig, ax = panel_grid(
        1, 1, subfig=subfig, figsize=(ONE_AND_HALF_COLUMN, 2.5)
    )
    ax = ax[0, 0]
    plot_ratio_swarm(ax, rows, ticks=(0.7, 0.8, 0.9, 1.0, 1.1, 1.25))
    ax.set_xlabel(f"{SCORE_LABELS[ev.scale]} relative to {LABELS['county']}")
    heading = resolve_title(
        title,
        "one county is a pair of dots, one per seed" if replicate is not None else None,
    )
    if heading is not None:
        ax.set_title(heading, fontsize=6.5)
    return fig
