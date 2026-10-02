"""Loading, scoring and the manuscript figures for Demo 1.

Imported by both `evaluation.ipynb` and `export.py`, so a figure in
the paper and the same figure in the notebook come from one function. The notebook
explores; the exporter emits only the canonical subset.

Figure numbering follows `drafts/figure-plan-v01.md`.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import Normalize

from manuscript_analysis.demos import paths
from manuscript_analysis.demos.lib.contacts import contact_matrix
from manuscript_analysis.demos.lib.figures import (
    AUTO_TITLE,
    DOUBLE_COLUMN,
    ONE_AND_HALF_COLUMN,
    SINGLE_COLUMN,
    resolve_title,
)
from manuscript_analysis.demos.lib.plots import (
    panel_grid,
    plot_contact_matrix,
    plot_line_panels,
    plot_quantile_grid,
    plot_ratio_swarm,
    plot_rolling_forecast_grid,
)
from manuscript_analysis.demos.lib.results import (
    align_observations,
    load_observations,
    load_runs,
    quantile_array,
)
from manuscript_analysis.demos.lib.scoring import (
    DEMO_QUANTILE_LEVELS,
    HEADLINE_SCALE,
    SCORE_LABELS,
    check_scale,
    interval_coverage,
    relative_wis,
    weighted_interval_score,
)

from .models import flu_season

__all__ = [
    "BASELINE",
    "COLORS",
    "Evaluation",
    "figure_calibration",
    "figure_contact_structures",
    "figure_eta_by_age",
    "figure_fit_by_age",
    "figure_relative_wis_swarm",
    "figure_rolling_forecasts",
    "figure_rolling_forecasts_by_age",
    "figure_wis_by_horizon",
    "focus_states",
    "load",
    "load_replicate",
    "relative_by_unit",
    "wis_by_jurisdiction",
]

MODELS = ("multi-strata-empirical", "multi-strata-homogeneous", "single-strata")
BASELINE = "single-strata"

# One mapping for the whole paper: the baseline is grey, added structure blue, structure
# that was degraded on purpose orange. See `drafts/figure-plan-v01.md`.
COLORS = {
    "multi-strata-empirical": "tab:blue",
    "multi-strata-homogeneous": "tab:orange",
    "single-strata": "tab:grey",
}
LABELS = {
    "multi-strata-empirical": "empirical mixing",
    "multi-strata-homogeneous": "homogeneous mixing",
    "single-strata": "no age structure",
}

# Which places the figures are drawn for. JM iterates on these; they live here rather
# than in `seasons.py`, which says what is forecast and *scored*, and rather than in the
# notebook, because `export_manuscript.py` needs the same answer. Two copies of this
# choice means the paper and the notebook can show different states.
FOCUS_STATE = "MN"
"""The state every single-state panel is drawn for."""

REFERENCE_STATES = ("MN", "AL", "WA", "TX", "AZ")
"""The states the multi-state panels show, in preference order.

Every score uses all 51 jurisdictions whatever this says; this is a figure choice only.
More are listed than any panel draws, so a panel can widen without editing the list.
"""

QUANTITY = "total"
AXIS_LABEL = "weekly admissions"
"""What every panel's y axis says. Demo 2's counterpart is `AXIS_LABELS`, which needs
one entry per quantity; Demo 1 forecasts a single quantity, so there is one label."""
DIMS = ["reference_date", "horizon", "location"]

# The seed-1 replicate. In the working folder it lived under `sensitivity/` with
# run-specific folder names, which is why `load` grew a `folders` argument; here both
# seeds name their folders for the model, so loading the replicate is a different seed
# and nothing else. `folders` is kept because it costs nothing and an output tree
# organised some other way is a fair thing to want to score.
REPLICATE_SEED = 1


class Evaluation(NamedTuple):
    """Everything the figures need, loaded and scored once."""

    runs: dict
    observations: pd.DataFrame
    forecasts: dict[str, np.ndarray]
    """Per model, `(origins, horizons, locations, levels)` on the scored jurisdictions."""
    observed: np.ndarray
    """`(origins, horizons, locations)`; identical for every model, and checked."""
    scores: dict
    scale: str
    """What `scores` are computed on: `"log"` (the manuscript's) or `"natural"`."""
    coverage: dict
    origins: np.ndarray
    horizons: np.ndarray
    locations: np.ndarray
    """FIPS codes, in the order of the array axes."""
    labels: dict[str, str]
    """FIPS code to postal abbreviation."""


def _with_total(observations: pd.DataFrame) -> pd.DataFrame:
    """Add the scoring target: the sum of the age bands, which is what models fit."""
    bands = observations[observations["quantity"].isin(flu_season.STRATA)]
    total = (
        bands.groupby(["date", "location"], as_index=False)["value"].sum()
        .assign(quantity=QUANTITY)
    )
    return pd.concat([observations, total], ignore_index=True)


def load(
    output_root: str | Path | None = None,
    models: Sequence[str] = MODELS,
    levels: Sequence[float] = DEMO_QUANTILE_LEVELS,
    folders: Mapping[str, str] | None = None,
    observations_csv: str | Path | None = None,
    scale: str = HEADLINE_SCALE,
) -> Evaluation:
    """Load every model's output, align it to the observations, and score it.

    `scale` names the scale the scores are computed on: `"log"`, the default and what
    the manuscript reports, transforms observations and forecasts by `log(x + 1)` before
    scoring; `"natural"` scores the counts as they are. Coverage is the same either way.

    `folders` maps a model name to the folder holding its run, for output trees whose
    folders are named for the run rather than for the model (`sensitivity/`). The name
    each folder's `run.json` declares is checked against the key, so a mapping that
    points at the wrong run fails here rather than producing a mislabelled figure.

    `observations_csv` defaults to `observations.csv` beside the runs. The replicate
    tree has none of its own: every run is scored against the one frozen file, which is
    the whole point of freezing it.
    """
    transform = check_scale(scale)
    output_root = Path(output_root or paths.runs("flu", seed=0))
    folders = dict(folders or {name: name for name in models})
    runs = load_runs(output_root, [folders[name] for name in models])
    runs = {name: runs[folders[name]] for name in models}
    for name, run in runs.items():
        declared = run.info["model"]
        if declared != name:
            raise ValueError(
                f"{output_root / folders[name]} holds model {declared!r}, "
                f"but it was loaded as {name!r}"
            )
    observations = _with_total(load_observations(
        observations_csv or paths.observations("flu")
    ))

    scored = flu_season.scored_locations()
    forecasts, observed_each, coords = {}, {}, {}
    for name, run in runs.items():
        frame = run.forecasts
        frame = frame[
            (frame["quantity"] == QUANTITY) & frame["location"].isin(scored)
        ]
        forecasts[name], coords[name] = quantile_array(frame, DIMS, levels=levels)
        observed_each[name] = align_observations(
            frame, DIMS, observations, quantity=QUANTITY
        )

    reference = observed_each[models[0]]
    for name in models[1:]:
        if not np.array_equal(observed_each[name], reference):
            raise ValueError(f"{name} was scored against different observations")

    scores = {
        name: weighted_interval_score(reference, forecasts[name], levels, transform)
        for name in models
    }
    coverage = {
        nominal: {
            name: interval_coverage(reference, forecasts[name], levels, nominal=nominal)
            for name in models
        }
        for nominal in (0.95, 0.50)
    }

    first = coords[models[0]]
    return Evaluation(
        runs=runs,
        observations=observations,
        forecasts=forecasts,
        observed=reference,
        scores=scores,
        scale=scale,
        coverage=coverage,
        origins=first["reference_date"],
        horizons=first["horizon"],
        locations=first["location"],
        labels=flu_season.location_labels(),
    )


def load_replicate(
    models: Sequence[str] = MODELS,
    levels: Sequence[float] = DEMO_QUANTILE_LEVELS,
    scale: str = HEADLINE_SCALE,
) -> Evaluation:
    """The seed-1 replicate of the manuscript run, scored identically.

    The denominator must be built exactly like the numerator, so this loads all three
    models at seed 1 rather than pairing a seed-1 model against the seed-0 baseline.
    Two earlier analyses were wrong in precisely that way; see `sensitivity/README.md`.
    """
    return load(
        output_root=paths.runs("flu", seed=REPLICATE_SEED),
        models=models,
        levels=levels,
        scale=scale,
    )


def wis_table(ev: Evaluation) -> pd.DataFrame:
    """Pooled and per-horizon WIS with coverage, one row per model.

    Columns are named for the scale, `WIS` or `log WIS`. The scores are arithmetic means;
    the relative column is the ratio of geometric means (`relative_wis`), so it is not
    simply one mean divided by another.
    """
    label = SCORE_LABELS[ev.scale]
    baseline = ev.scores[BASELINE].total
    return pd.DataFrame(
        {
            label: [ev.scores[m].total.mean() for m in ev.scores],
            **{
                f"h{h}": [ev.scores[m].total[:, i].mean() for m in ev.scores]
                for i, h in enumerate(ev.horizons)
            },
            f"rel {label}": [
                float(relative_wis(ev.scores[m].total, baseline))
                for m in ev.scores
            ],
            "cov95": [ev.coverage[0.95][m].mean() for m in ev.scores],
            "cov50": [ev.coverage[0.50][m].mean() for m in ev.scores],
        },
        index=list(ev.scores),
    )


def wis_by_jurisdiction(
    ev: Evaluation,
    models: Sequence[str] = MODELS,
    sort_by: str | None = None,
) -> pd.DataFrame:
    """Mean WIS per jurisdiction, one row per jurisdiction and one column per model.

    The model columns are arithmetic means on `ev.scale`; the ratio columns are relative
    WIS, the ratio of geometric means, exactly as Figure 2(d) draws them.

    The per-jurisdiction detail behind the pooled table and behind Figure 2(d), for the
    supplement. Ratios against the baseline are included because a column of raw WIS is
    dominated by population and invites comparing California against Wyoming, which is
    not a comparison anyone should make.

    `sort_by` takes a column name, most usefully the ratio column of the model being
    argued for. Defaults to alphabetical by jurisdiction, which is what a reference
    table wants.
    """
    frame = pd.DataFrame(
        {"jurisdiction": [ev.labels[code] for code in ev.locations],
         "fips": list(ev.locations)}
    )
    for model in models:
        frame[model] = ev.scores[model].total.mean(axis=(0, 1))
    for model in models:
        if model != BASELINE:
            frame[f"{model} / {BASELINE}"] = relative_by_unit(ev, model)

    if sort_by is not None:
        if sort_by not in frame.columns:
            raise ValueError(
                f"no column {sort_by!r}; the table holds {list(frame.columns)}"
            )
        frame = frame.sort_values(sort_by)
    else:
        frame = frame.sort_values("jurisdiction")
    return frame.set_index("jurisdiction")


def relative_by_unit(ev: Evaluation, model: str) -> np.ndarray:
    """Per-jurisdiction relative WIS against the baseline; below 1 means `model` is better.

    The ratio of geometric means over origins and horizons, on `ev.scale`. Named for the
    *unit* rather than the jurisdiction so Demo 1 and Demo 2 can use one
    name for one idea; Demo 2's units are counties.
    """
    return relative_wis(
        ev.scores[model].total, ev.scores[BASELINE].total, axis=(0, 1)
    )


# Backwards-compatible alias: the notebook and the sensitivity analyses call this.
relative_by_state = relative_by_unit


def focus_states(ev: Evaluation, count: int = 3) -> list[str]:
    """The first `count` of `REFERENCE_STATES` that this evaluation actually scores.

    Demo 2's counterpart is `focus_counties`. Filtered against what was scored so that a
    run over a subset of jurisdictions still draws, rather than raising on a state that
    is not in the output.
    """
    scored = {ev.labels[code] for code in ev.locations}
    chosen = [state for state in REFERENCE_STATES if state in scored][:count]
    if len(chosen) < count:
        raise ValueError(
            f"only {len(chosen)} of REFERENCE_STATES were scored; "
            f"this run holds {len(scored)} jurisdictions"
        )
    return chosen


def figure_contact_structures(
    state: str = "CA",
    mixings: Sequence[str] = ("empirical", "homogeneous"),
    title: str | None = AUTO_TITLE,
    subfig=None,
):
    """Figure 2(a): the contact structures the two stratified models actually use.

    Demo 2's opening panel is its commuting matrix; this is the counterpart, and the two
    together are what make the demos read as one argument run twice rather than as two
    case studies. See `demo-covid/evaluation.figure_movement_structure`.

    **Both panels share one colour scale**, because the comparison is the whole point and
    panels on independent scales invite exactly the wrong reading. Every matrix is
    normalized to unit spectral radius before it reaches a model, so the two cannot differ
    in their leading eigenvalue, only in its eigenvector: the comparison tests the *shape*
    of mixing while leaving overall transmissibility free for `q(t)` to fit.

    Drawn for one state because the empirical matrix is projected onto that state's own
    demography. The projection is mild and the choice is not load-bearing; see
    `old/contact-matrix-methods.md` section 9.

    `title` takes a string, or None to draw none; see `manuscript_analysis.demos.lib.figures.resolve_title`.

    This replaces the generator in `old/contact-matrices.ipynb`, which no longer runs
    since `demolib/contacts.py` was trimmed. Before this, `figures/figS1_contact_structures`
    was a manuscript figure with no live code that could reproduce it.
    """
    node = list(flu_season.scope().node_ids).index(
        {abbr: code for code, abbr in flu_season.location_labels().items()}[state]
    )
    populations = flu_season.demography().by_stratum
    matrices = [
        contact_matrix(flu_season.contact_source(), populations, mixing=mixing)[node]
        for mixing in mixings
    ]

    if subfig is None:
        fig = plt.figure(
            figsize=(SINGLE_COLUMN * len(mixings), 2.6), layout="constrained"
        )
    else:
        fig = subfig
    axs = np.atleast_1d(fig.subplots(1, len(mixings)))

    shared = Normalize(vmin=0.0, vmax=float(np.max(matrices)))
    labels = list(flu_season.STRATA_LABELS)
    for ax, mixing, matrix in zip(axs, mixings, matrices):
        image = plot_contact_matrix(
            ax, matrix, labels, title=mixing.replace("_", " "), norm=shared,
        )
    bar = fig.colorbar(image, ax=list(axs), fraction=0.046, pad=0.03)
    bar.set_label("contact rate (spectral radius 1)", fontsize=6)
    bar.ax.tick_params(labelsize=5)
    heading = resolve_title(title, f"Contact structure, {state}")
    if heading is not None:
        fig.suptitle(heading)
    return fig


def figure_fit_by_age(
    ev: Evaluation,
    state: str,
    model: str,
    series: str = "prior",
    levels=DEMO_QUANTILE_LEVELS,
    ncols: int = 3,
    title: str | None = AUTO_TITLE,
    subfig=None,
    color: str | None = None,
):
    """Figure 2(a): the weekly fit against observed admissions, by age band.

    The only panel that shows the model fitting six channels rather than one.

    `series` defaults to **prior**, the one-week-ahead prediction taken *before* the
    Kalman update, because that is a genuine prediction. The posterior is taken after
    the update and is pulled onto the observation by construction, so it always looks
    good and is evidence of very little. Pass `series="posterior"` to see how hard the
    filter had to work; the gap between the two is the interesting quantity.

    Six bands over `ncols` columns, drawn by `manuscript_analysis.demos.lib.plots.plot_quantile_grid`, which is
    the same function Demo 2's `figure_fit` uses; only what a row means differs. At the
    default three columns the six bands fill two rows, and the dates are printed once,
    under the bottom row.
    """
    if series not in ("prior", "posterior"):
        raise ValueError(f"series must be 'prior' or 'posterior', got {series!r}")
    fips = {abbr: code for code, abbr in ev.labels.items()}[state]
    fit = ev.runs[model].fit
    fit = fit[(fit["series"] == series) & (fit["location"] == fips)]

    panels = []
    for band, label in zip(flu_season.STRATA, flu_season.STRATA_LABELS):
        band_fit = fit[fit["quantity"] == band]
        values, coords = quantile_array(band_fit, ["target_end_date"], levels=levels)
        dates = pd.to_datetime(coords["target_end_date"])
        seen = ev.observations[
            (ev.observations["quantity"] == band)
            & (ev.observations["location"] == fips)
            & (ev.observations["date"].isin(dates))
        ].sort_values("date")
        panels.append({
            "dates": dates,
            "quantiles": {q: values[:, i] for i, q in enumerate(levels)},
            "observed": seen["value"].to_numpy(),
            "color": color or COLORS[model],
            "title": label,
        })

    fig, _ = plot_quantile_grid(
        panels,
        ncols=ncols,
        style="bars",
        ylabels=AXIS_LABEL,
        title=resolve_title(title, (
            f"{LABELS[model]}, {state}: "
            + ("one-week-ahead prediction, before the filter update"
               if series == "prior" else "posterior, after the filter update")
        )),
        figure_width=DOUBLE_COLUMN,
        panel_height=1.8,
        subfig=subfig,
    )
    return fig


def figure_rolling_forecasts(
    ev: Evaluation,
    states: Sequence[str],
    model: str,
    levels=DEMO_QUANTILE_LEVELS,
    title: str | None = AUTO_TITLE,
    subfig=None,
    color: str | None = None,
):
    """Figure 2(b): every origin's forecast fan against the observed series.

    One panel per state, drawn by `manuscript_analysis.demos.lib.plots.plot_rolling_forecast_grid`, which also
    draws `figure_rolling_forecasts_by_age` and Demo 2's `figure_rolling_forecasts`.
    """
    fips_of = {abbr: code for code, abbr in ev.labels.items()}
    index = {code: i for i, code in enumerate(ev.locations)}

    panels = []
    for state in states:
        node = index[fips_of[state]]
        seen = ev.observations[
            (ev.observations["quantity"] == QUANTITY)
            & (ev.observations["location"] == fips_of[state])
        ].sort_values("date")
        panels.append({
            "origins": ev.origins,
            "horizons": ev.horizons,
            "values": ev.forecasts[model][:, :, node, :],
            "observed": (seen["date"].to_numpy(), seen["value"].to_numpy()),
            "color": color or COLORS[model],
            "title": state,
        })

    fig, _ = plot_rolling_forecast_grid(
        panels,
        levels,
        ylabels=AXIS_LABEL,
        title=resolve_title(title, f"Rolling forecasts, {LABELS[model]}"),
        figure_width=DOUBLE_COLUMN,
        panel_height=2.0,
        subfig=subfig,
    )
    return fig


def figure_rolling_forecasts_by_age(
    ev: Evaluation,
    state: str,
    model: str,
    levels=DEMO_QUANTILE_LEVELS,
    quantities: Sequence[str] | None = None,
    ncols: int = 3,
    title: str | None = AUTO_TITLE,
    subfig=None,
    color: str | None = None,
):
    """Figure 2(b), age-resolved: one state, one panel per age band.

    The companion to `figure_rolling_forecasts`, which shows several states at the
    scoring target (the sum of the bands). This shows where that sum comes from, and
    is the only forecast panel that makes the six fitted channels visible.

    Reads the per-age forecasts straight from the run rather than from `ev.forecasts`,
    which holds only the scored total.
    """
    quantities = list(quantities or flu_season.STRATA)
    fips = {abbr: code for code, abbr in ev.labels.items()}[state]

    frame = ev.runs[model].forecasts
    frame = frame[frame["location"] == fips]
    available = set(frame["quantity"].unique())
    missing = [q for q in quantities if q not in available]
    if missing:
        raise ValueError(
            f"{model} has no forecasts for {missing}; it holds {sorted(available)}"
        )

    panels = []
    for quantity in quantities:
        band = frame[frame["quantity"] == quantity]
        values, coords = quantile_array(
            band, ["reference_date", "horizon"], levels=levels
        )
        seen = ev.observations[
            (ev.observations["quantity"] == quantity)
            & (ev.observations["location"] == fips)
        ].sort_values("date")
        panels.append({
            "origins": coords["reference_date"],
            "horizons": coords["horizon"],
            "values": values,
            "observed": (seen["date"].to_numpy(), seen["value"].to_numpy()),
            "color": color or COLORS[model],
            "title": quantity.removeprefix("age_"),
        })

    fig, _ = plot_rolling_forecast_grid(
        panels,
        levels,
        ncols=ncols,
        ylabels=AXIS_LABEL,
        title=resolve_title(
            title, f"{LABELS[model]}, {state}: rolling forecasts by age"
        ),
        figure_width=DOUBLE_COLUMN,
        panel_height=1.7,
        subfig=subfig,
    )
    return fig


def figure_eta_by_age(
    ev: Evaluation,
    state: str,
    model: str,
    levels=DEMO_QUANTILE_LEVELS,
    ncols: int = 3,
    title: str | None = AUTO_TITLE,
    subfig=None,
):
    """The per-age contact correction `exp(eta_i)` through the season, one state.

    Section 8's table reports the `eta_i` at the final date only. This shows the whole
    trajectory, which is where the filter's age-specific learning is actually visible.

    Only *differences* between the `eta_i` are identified: a shift common to all six is
    indistinguishable from a shift in `q(t)`. Each date is therefore recentred by the
    mean of the six medians at that date, which is one scalar per date and so a
    monotone shift of every quantile rather than a reordering of them.

    Bands rather than bars, unlike the fit panels: the correction is a continuous
    process being tracked, not a sequence of separate predictions.
    """
    fips = {abbr: code for code, abbr in ev.labels.items()}[state]
    params = ev.runs[model].params
    params = params[params["location"] == fips]

    names = sorted(n for n in params["parameter"].unique() if "log_eta" in n)
    if not names:
        raise ValueError(
            f"{model} estimates no log_eta, so it has no per-age correction to show"
        )

    levels = list(levels)
    median = levels.index(0.5)

    stacked, dates = [], None
    for name in names:
        values, coords = quantile_array(
            params[params["parameter"] == name], ["date"], levels=levels
        )
        stacked.append(values)
        dates = pd.to_datetime(coords["date"])
    stacked = np.stack(stacked)                        # (bands, dates, levels)
    common = stacked[:, :, median].mean(axis=0)        # absorbed by q(t)
    centred = stacked - common[None, :, None]

    panels = []
    for label, band in zip(flu_season.STRATA_LABELS, centred):
        panels.append({
            "dates": dates,
            "quantiles": {q: np.exp(band[:, i]) for i, q in enumerate(levels)},
            "color": COLORS[model],
            "title": label,
            "reference": 1.0,
        })

    fig, _ = plot_quantile_grid(
        panels,
        ncols=ncols,
        style="bands",
        ylabels="contact multiplier\nexp(centred eta)",
        reference_label="no correction",
        title=resolve_title(
            title, f"{LABELS[model]}, {state}: per-age contact correction"
        ),
        figure_width=DOUBLE_COLUMN,
        panel_height=1.7,
        sharey=True,
        subfig=subfig,
    )
    return fig


def figure_wis_by_horizon(
    ev: Evaluation,
    title: str | None = None,
    subfig=None,
    legend: bool | str = True,
):
    """Figure 2(c): forecast skill against horizon, one line per model.

    One panel, where Demo 2 has one per quantity, but both are drawn by
    `manuscript_analysis.demos.lib.plots.plot_line_panels` so the two demos' skill curves match.
    """
    series = {
        LABELS[model]: ev.scores[model].total.mean(axis=(0, 2))[np.newaxis, :]
        for model in ev.scores
    }
    fig, _ = plot_line_panels(
        ev.horizons,
        series,
        colors={LABELS[model]: COLORS[model] for model in ev.scores},
        ylabel=SCORE_LABELS[ev.scale],
        xlabel="horizon (weeks ahead)",
        xticks=ev.horizons,
        suptitle=title,
        legend=legend,
        legend_loc="upper left",
        figure_width=SINGLE_COLUMN,
        panel_height=2.3,
        subfig=subfig,
    )
    return fig


def figure_calibration(
    ev: Evaluation,
    nominal: float = 0.95,
    title: str | None = None,
    subfig=None,
    legend: bool | str = True,
):
    """Interval coverage against nominal, one line per model.

    Demo 1's half of the supplementary calibration figure (`export_manuscript`), and the
    counterpart to Demo 2's `figure_calibration`: same helper, same encoding, one panel instead of two
    because Demo 1 scores one quantity. All three models are under-dispersed, which is
    an honest limitation rather than something to bury.
    """
    series = {
        LABELS[model]: np.array([[
            ev.coverage[nominal][model][:, i].mean()
            for i in range(len(ev.horizons))
        ]])
        for model in ev.scores
    }
    fig, _ = plot_line_panels(
        ev.horizons,
        series,
        colors={LABELS[model]: COLORS[model] for model in ev.scores},
        ylabel=f"{nominal:.0%} interval coverage",
        xlabel="horizon (weeks ahead)",
        xticks=ev.horizons,
        ylim=(0, 1),
        reference=nominal,
        reference_label="nominal",
        suptitle=title,
        legend=legend,
        figure_width=SINGLE_COLUMN,
        panel_height=2.3,
        subfig=subfig,
    )
    return fig


def figure_relative_wis_swarm(
    ev: Evaluation,
    replicate: Evaluation | None = None,
    models: Sequence[str] = ("multi-strata-empirical", "multi-strata-homogeneous"),
    title: str | None = AUTO_TITLE,
    subfig=None,
):
    """Figure 2(d): both models' per-jurisdiction WIS ratio against the baseline.

    One row per model, so the paper's actual claim reads off the figure: the benefit
    comes from the contact data, not from stratifying. The empirical row sits left of 1;
    the homogeneous row straddles it.

    The drawing is `manuscript_analysis.demos.lib.plots.plot_ratio_swarm`, shared with Demo 2's county-level
    version, so the two demos' headline distributions cannot drift apart stylistically.
    Each jurisdiction is a pair of dots joined by a line, one per seed; pass
    `replicate=None` for seed 0 alone.

    Per-jurisdiction assignment is not reproducible even at R = 300, and this figure is
    built to show that rather than hide it: the jurisdictions whose two dots are far apart
    are the ones whose ranking should not be read. The default title says so, which is
    why it is a title rather than a caption; pass `title=None` to drop it.
    """
    rows = []
    for model in models:
        seeds = [relative_by_unit(ev, model)]
        if replicate is not None:
            seeds.append(relative_by_unit(replicate, model))
        rows.append({"label": LABELS[model], "color": COLORS[model], "seeds": seeds})

    fig, ax = panel_grid(1, 1, subfig=subfig, figsize=(ONE_AND_HALF_COLUMN, 2.5))
    ax = ax[0, 0]
    # Relative log WIS sits much closer to 1 than natural-scale ratios did.
    plot_ratio_swarm(ax, rows, ticks=(0.8, 0.9, 1.0, 1.1, 1.25, 1.5))
    ax.set_xlabel(f"{SCORE_LABELS[ev.scale]} relative to {LABELS[BASELINE]}")
    heading = resolve_title(
        title,
        "one jurisdiction is a pair of dots, one per seed"
        if replicate is not None else None,
    )
    if heading is not None:
        ax.set_title(heading, fontsize=6.5)
    return fig
