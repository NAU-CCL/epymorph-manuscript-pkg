"""Everything the COVID models share.

Every ingredient that is not resolution or movement lives here: geography, demography,
the two observed quantities and their imputation, initial conditions and priors. The
model modules import from this and add only what distinguishes them.

Accessors are memoized, so importing all three model modules fetches once.

Reasoning behind the values below: `project-notes/handoff.md` (the region, the MMWR week
alignment, severity identification, the shared seeding) and `demo-covid/old/ifr-methods.md`.
"""

from functools import cache
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd
from epymorph.adrio import cdc
from epymorph.adrio.acs5 import Population
from epymorph.adrio.commuting_flows import Commuters
from epymorph.adrio.us_tiger import InternalPoint
from epymorph.forecasting.dynamic_params import GaussianPrior, OrnsteinUhlenbeck
from epymorph.forecasting.pipeline import UnknownParam
from epymorph.geography.us_census import CountyScope, StateScope
from epymorph.time import TimeFrame
from epymorph.util import pairwise_haversine, to_date_value_array
from scipy.stats import poisson

from manuscript_analysis.data import ProvenanceCachedADRIO
from manuscript_analysis.demos.lib.forecasting import Quantity
from manuscript_analysis.demos.lib.ipms.covid_seirhd import (
    CENSUS_COMPARTMENT,
    DEATHS_EVENT,
    SEIRHD,
)

from ... import paths
from ..seasons import COVID_2020, Season
from .correlated_ou import CorrelatedOU, spatial_correlation

SEASON = COVID_2020

DEMO_DIR = paths.RUNS / "covid"
"""Kept for callers that want the demo's output root; see `paths`."""
OBSERVATIONS_CSV = paths.observations("covid")

QUANTITIES = ("census", "deaths")
"""The two observed quantities: a hospital census (a stock) and deaths (a flow).

They are not commensurate, so they must never be summed. See
`demo-covid/refactor-plan-v01.md`.
"""

# --- natural history ---------------------------------------------------------

LATENT_DAYS = 3.0
INFECTIOUS_DAYS = 6.0
HOSPITAL_DAYS = 7.0  # measured: season patient-days / admissions = 6.97
IMMUNE_DAYS = 365.0

SIGMA = 1 / LATENT_DAYS
GAMMA = 1 / INFECTIOUS_DAYS
XI = 1 / IMMUNE_DAYS

# --- severity ----------------------------------------------------------------

HOSPITALIZATION_PROB = 0.048
DEATH_PROB = 0.22
"""Deaths per hospitalization-equivalent, not in-hospital mortality.

The IPM routes every death through H while NCHS counts out-of-hospital deaths, and the
observed census counts confirmed inpatients only, so this is necessarily above any
published in-hospital figure. A per-node deviation is estimated.
"""
BETA = 0.20

# --- initial conditions ------------------------------------------------------

LOWER_IMMUNE, UPPER_IMMUNE = 0.05, 0.15
LOWER_INFECTED, UPPER_INFECTED = 0.2 / 1000, 1.0 / 1000
COUNTY_JITTER = 0.25

# Independent substreams, so the state-level draw for state "25" cannot collide with the
# jitter draw for a county whose FIPS happens to share its integer value.
STREAM_STATE_LEVEL = 0
STREAM_COUNTY_JITTER = 1

# --- suppressed deaths -------------------------------------------------------

SUPPRESSED_LO, SUPPRESSED_HI = 1, 9
FILL_SEED = 0

# --- what the filter estimates -----------------------------------------------

BETA_PRIOR_SD = 0.30
BETA_OU_SD = 0.45
BETA_DAMPING = 1 / 150
DEATH_PROB_PRIOR_SD = 0.15
DEATH_PROB_OU_SD = 0.15
DEATH_PROB_DAMPING = 1 / 150

# --- spatially correlated parameter shocks (a sensitivity analysis) -------------


class SpatialCorrelation(NamedTuple):
    """How strongly the counties' parameter shocks move together.

    Each parameter's correlation matrix is `shared * exp(-d / length_scale) +
    (1 - shared) * I`, with `d` the distance between county internal points in miles.
    """

    length_scale: float
    """Miles."""
    beta_shared: float
    death_prob_shared: float


CORRELATION_FITTED = SpatialCorrelation(
    length_scale=200.0, beta_shared=0.3, death_prob_shared=0.1
)
"""Fitted, without forecast scores, to the week-to-week changes in the filtered log beta
of the independent county models, and separately to the weekly growth of the observed
census; the two agree on about 200 miles and a shared fraction of about 0.3. Death_prob
changes correlate at only about 0.1 with no clear decay in distance, so it keeps the
length scale and takes a small shared fraction.
"""

CORRELATION_STRONG = SpatialCorrelation(
    length_scale=200.0, beta_shared=1.0, death_prob_shared=1.0
)
"""A pure exponential kernel, the form in `FluSight-pipeline/flu/correlated.py`. Mean
county-pair correlation 0.64, about three times what the data show: an upper bracket.
"""


def season() -> Season:
    return SEASON


@cache
def scope() -> CountyScope:
    """The county scope the movement and county models run on."""
    return CountyScope.in_states(list(SEASON.states), year=SEASON.census_year)


@cache
def state_scope() -> StateScope:
    """The state scope the aggregate model runs on, and the scale all three are scored on."""
    return StateScope.in_states(list(SEASON.states), year=SEASON.census_year)


@cache
def cdc_scope() -> CountyScope:
    """The county vintage the CDC datasets are keyed on."""
    found = CountyScope.in_states(list(SEASON.states), year=SEASON.cdc_year)
    if list(found.node_ids) != list(scope().node_ids):
        raise ValueError(
            f"county sets differ between {SEASON.census_year} and {SEASON.cdc_year}"
        )
    return found


@cache
def time_frame() -> TimeFrame:
    return TimeFrame.of(start_date=SEASON.start_date, duration_days=7 * SEASON.weeks)


def _frozen(adrio, name: str, what: str) -> ProvenanceCachedADRIO:
    """`adrio`, read from `data/raw/` once it is frozen there.

    The first call fetches it, which needs the Census API key, and freezes it with its
    provenance; every later call, on any machine, reads the file. The file is named for the
    season's states and ACS vintage, so a changed season gets its own file rather than
    reading a stale one.
    """
    states = "-".join(SEASON.states).lower()
    return ProvenanceCachedADRIO(
        adrio,
        cache_path=paths.RAW / f"covid-{name}-{SEASON.census_year}-{states}.npz",
        description=f"{what}; {SEASON.census_year} vintage; {', '.join(SEASON.states)}",
    )


@cache
def population() -> np.ndarray:
    return (
        _frozen(Population(), "population-counties", "ACS 5-year population per county")
        .with_context(scope=scope(), time_frame=time_frame())
        .inspect().result.astype(np.int64)
    )


@cache
def state_population() -> np.ndarray:
    return (
        _frozen(Population(), "population-states", "ACS 5-year population per state")
        .with_context(scope=state_scope(), time_frame=time_frame())
        .inspect().result.astype(np.int64)
    )


@cache
def to_states() -> np.ndarray:
    """`(states, counties)`, so `to_states @ county_values` sums each state's counties."""
    county_state = np.array([node[:2] for node in scope().node_ids])
    matrix = np.zeros((state_scope().nodes, scope().nodes))
    for i, state in enumerate(state_scope().node_ids):
        matrix[i, county_state == state] = 1.0
    if not (matrix.sum(axis=0) == 1).all():
        raise ValueError("every county must belong to exactly one state")
    return matrix


def state_series(county_values: np.ndarray) -> np.ndarray:
    """Sum a `(T, counties)` series to `(T, states)`."""
    return county_values @ to_states().T


@cache
def state_of_county() -> np.ndarray:
    """For each county, the index of its state in the state scope."""
    return np.argmax(to_states(), axis=0)


@cache
def commuters() -> np.ndarray:
    """The commuting flows the movement model uses, and nothing else does."""
    flows = np.asarray(
        _frozen(Commuters(), "commuters-counties", "ACS commuting flows between counties")
        .with_context(scope=scope(), time_frame=time_frame())
        .inspect().result
    ).astype(np.int64)
    if flows.shape != (scope().nodes, scope().nodes):
        raise ValueError(f"commuters is {flows.shape}, expected a square county matrix")
    return flows


@cache
def county_distances() -> np.ndarray:
    """`(counties, counties)` great-circle miles between county internal points."""
    points = (
        InternalPoint().with_context(scope=scope(), time_frame=time_frame()).inspect().result
    )
    return pairwise_haversine(points, units="miles")


def parameter_cholesky(correlation: SpatialCorrelation) -> dict[str, np.ndarray]:
    """The Cholesky factor of each estimated parameter's county correlation matrix."""
    distances = county_distances()
    shared = {
        "log_beta": correlation.beta_shared,
        "log_death_prob": correlation.death_prob_shared,
    }
    factors = {}
    for name, fraction in shared.items():
        matrix = spatial_correlation(distances, correlation.length_scale, fraction)
        factors[name] = np.linalg.cholesky(matrix)
    return factors


class Observed(NamedTuple):
    census: np.ndarray
    """(T, counties) mean daily hospital census, a stock."""
    deaths: np.ndarray
    """(T, counties) weekly deaths with suppressed cells imputed, a flow."""
    suppressed: np.ndarray
    """(T, counties) True where the true death count was censored to 1-9."""
    census_dates: np.ndarray
    death_dates: np.ndarray
    """The two quantities label the same MMWR week at opposite ends, six days apart."""


def _impute_suppressed(lam: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Draw from Poisson(lam) truncated to the censoring interval {LO, ..., HI}."""
    k = np.arange(SUPPRESSED_LO, SUPPRESSED_HI + 1)
    weights = poisson.pmf(k[:, None], np.maximum(lam.ravel(), 1e-9)[None, :])
    totals = weights.sum(axis=0, keepdims=True)
    degenerate = (totals <= 0).ravel()
    weights = np.where(totals > 0, weights / np.maximum(totals, 1e-300), 0.0)
    draw = (rng.random(weights.shape[1])[None, :] > np.cumsum(weights, axis=0)).sum(axis=0)
    out = k[np.clip(draw, 0, len(k) - 1)]
    out[degenerate] = SUPPRESSED_HI
    return out.reshape(lam.shape)


def fetch_observations(path: Path = OBSERVATIONS_CSV) -> Path:
    """Fetch both quantities from CDC, impute suppressed deaths, write a tidy CSV.

    Freezing this is load-bearing here, more than for the flu demo: the imputation is a
    random draw, so re-deriving it would change the target the models are scored against.
    """
    context = {"scope": cdc_scope(), "time_frame": time_frame()}

    deaths_raw = (
        cdc.CountyDeaths(cause_of_death="COVID-19", fix_redacted=False, fix_missing=False)
        .with_context(**context).inspect().result
    )
    death_dates = np.ma.getdata(deaths_raw["date"])[:, 0]
    suppressed = np.ma.getmaskarray(deaths_raw["value"])
    observed = np.ma.getdata(deaths_raw["value"]).astype(np.float64)

    census_raw = (
        cdc.COVIDFacilityHospitalization(
            age_group="both", fix_redacted=2, fix_missing=False
        ).with_context(**context).inspect().result
    )
    if np.ma.getmaskarray(census_raw["value"]).any():
        raise ValueError("hospital census is masked; the EnKF cannot take a masked source")
    census = np.ma.getdata(census_raw["value"]).astype(np.float64) / 7.0
    census_dates = np.ma.getdata(census_raw["date"])[:, 0]

    offset = (death_dates[0] - census_dates[0]).astype(int)
    if offset != 6:
        raise ValueError(
            f"the two quantities are {offset} days apart, expected 6; "
            "they are not bracketing the same MMWR week"
        )

    # Impute the censored cells from the region's own per-capita mortality that week.
    weeks = SEASON.weeks
    pops = population()
    weekly_regional = np.where(suppressed, 0, observed).sum(axis=1)
    pop_reporting = np.array(
        [pops[~suppressed[t]].sum() for t in range(weeks)], dtype=np.float64
    )
    lam = (weekly_regional / pop_reporting)[:, None] * pops[None, :]
    filled = _impute_suppressed(lam, np.random.default_rng(FILL_SEED))
    deaths = np.where(suppressed, filled, observed).astype(np.float64)

    frames = []
    for name, values, dates in (
        ("census", census, census_dates),
        ("deaths", deaths, death_dates),
    ):
        for node, location in enumerate(scope().node_ids):
            frames.append(pd.DataFrame({
                "date": dates,
                "location": location,
                "quantity": name,
                "value": values[:, node],
                "suppressed": suppressed[:, node] if name == "deaths" else False,
            }))
    table = pd.concat(frames, ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    table.sort_values(["quantity", "date", "location"]).to_csv(path, index=False)
    return path


def _observations_mismatch(path: Path) -> str:
    """Why the frozen file does not answer for this season, or an empty string."""
    table = pd.read_csv(path, dtype={"location": str}, parse_dates=["date"])
    weeks = table[table["quantity"] == QUANTITIES[0]]["date"].nunique()
    if weeks != SEASON.weeks:
        return f"covers {weeks} weeks, the season wants {SEASON.weeks}"
    first = table["date"].min().date()
    if first != SEASON.start_date:
        return f"starts {first}, the season starts {SEASON.start_date}"
    stored = set(table["location"].unique())
    wanted = set(scope().node_ids)
    if stored != wanted:
        return f"holds {len(stored)} locations, the season wants {len(wanted)}"
    return ""


@cache
def observations(path: Path = OBSERVATIONS_CSV) -> Observed:
    """Both quantities, loaded from the frozen CSV.

    The file is evidence: it is the target every model is scored against. If it is
    missing, or does not cover the season's window and locations, this stops rather than
    fetching; `fetch_observations()` is the deliberate way to replace it. (A refetch is
    deterministic despite the suppressed-death imputation, which draws from
    `np.random.default_rng(FILL_SEED)`.)
    """
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is missing. It is frozen evidence and is not refetched "
            "automatically: restore it from git, or call fetch_observations()."
        )
    stale = _observations_mismatch(path)
    if stale:
        raise ValueError(
            f"{path.name} does not match the season: {stale}. It is not refetched "
            "automatically; call fetch_observations() to replace it deliberately."
        )
    table = pd.read_csv(path, dtype={"location": str}, parse_dates=["date"])
    locations = list(scope().node_ids)

    def channel(name):
        part = table[table["quantity"] == name]
        dates = np.array(sorted(part["date"].unique()))
        pivot = part.pivot_table(index="date", columns="location", values="value")
        return np.stack([pivot[loc].to_numpy() for loc in locations], axis=1), dates

    census, census_dates = channel("census")
    deaths, death_dates = channel("deaths")
    flags = table[table["quantity"] == "deaths"].pivot_table(
        index="date", columns="location", values="suppressed"
    )
    suppressed = np.stack([flags[loc].to_numpy() for loc in locations], axis=1).astype(bool)
    return Observed(
        census, deaths, suppressed,
        census_dates.astype("datetime64[D]"), death_dates.astype("datetime64[D]"),
    )


def observation_source(*, aggregated: bool) -> np.ndarray:
    """A `(weeks, nodes, 2)` date-value array; the Q axis is census then deaths.

    The two quantities carry different dates because they label the same MMWR week at
    opposite ends, so the array is built per quantity rather than broadcast.
    """
    obs = observations()
    census = state_series(obs.census) if aggregated else obs.census
    deaths = state_series(obs.deaths) if aggregated else obs.deaths

    source = np.empty(
        (SEASON.weeks, census.shape[1], 2),
        dtype=to_date_value_array(obs.census_dates[:1], census[:1, :1]).dtype,
    )
    source["date"][:, :, 0] = obs.census_dates[:, None]
    source["date"][:, :, 1] = obs.death_dates[:, None]
    source["value"][:, :, 0] = census
    source["value"][:, :, 1] = deaths
    return source


def _node_generator(
    rng: np.random.Generator, location: str, stream: int
) -> np.random.Generator:
    """An independent stream for one node, keyed by its FIPS code.

    Drawing every node from one shared stream makes each node's values depend on how many
    other nodes there are and where it sits in the list, so adding or dropping a
    jurisdiction silently changes the initial conditions of every other one. Keying on the
    FIPS code instead means a node's draws depend only on the run seed and on which node it
    is. Ported from `demo-flu/models/flu_season.py`, where the same bug was found first.
    """
    parent = rng.bit_generator.seed_seq
    child = np.random.SeedSequence(
        entropy=parent.entropy,
        spawn_key=(*parent.spawn_key, stream, int(location)),
    )
    return np.random.default_rng(child)


def _draw_state_fractions(
    num_realizations: int, rng: np.random.Generator
) -> dict[str, np.ndarray]:
    """One immune / infected / exposed fraction per state per realization.

    Keyed on the state's FIPS code off the run's own seed, which buys three things at
    once. All three models are handed the SAME state-level values, because they are always
    run at the same seed and the provenance check enforces it, so their aggregate initial
    conditions are identical by construction rather than accidentally different. A
    different seed now gives different state-level values, which a hardcoded stream did
    not: the state model's prior was previously identical at every seed, making its seed
    replicate a test of filter noise alone. And the roster no longer matters.

    Draw order within a node's stream is fixed (immune, infected, exposed) and must stay
    that way, or every number changes.
    """
    fractions = {
        name: np.zeros((num_realizations, state_scope().nodes))
        for name in ("immune", "infected", "exposed")
    }
    for index, state in enumerate(state_scope().node_ids):
        node_rng = _node_generator(rng, state, STREAM_STATE_LEVEL)
        fractions["immune"][:, index] = node_rng.uniform(
            LOWER_IMMUNE, UPPER_IMMUNE, size=num_realizations
        )
        fractions["infected"][:, index] = node_rng.uniform(
            LOWER_INFECTED, UPPER_INFECTED, size=num_realizations
        )
        fractions["exposed"][:, index] = node_rng.uniform(
            LOWER_INFECTED, UPPER_INFECTED, size=num_realizations
        )
    return fractions


def _draw_county_jitter(
    num_realizations: int, rng: np.random.Generator
) -> dict[str, np.ndarray]:
    """One multiplicative jitter per county per realization, per fraction.

    Three independent jitters rather than one shared one, preserving the previous
    behaviour: a county may sit above its state's level on immunity and below it on
    incidence.
    """
    jitter = {
        name: np.zeros((num_realizations, scope().nodes))
        for name in ("immune", "infected", "exposed")
    }
    for index, county in enumerate(scope().node_ids):
        node_rng = _node_generator(rng, county, STREAM_COUNTY_JITTER)
        for name in ("immune", "infected", "exposed"):
            jitter[name][:, index] = node_rng.uniform(
                1 - COUNTY_JITTER, 1 + COUNTY_JITTER, size=num_realizations
            )
    return jitter


def _initial_values(
    num_realizations: int, rng: np.random.Generator, *, aggregated: bool
) -> np.ndarray:
    """`(realizations, nodes, 6)` initial compartments, ordered S E I R H D.

    Counties within a state share a common immunity and incidence level, because they
    share an epidemic history. Drawing them independently asserts the opposite and shrinks
    the aggregate spread by about sqrt(k), handing the county models far less prior
    uncertainty than the state model at the scale they are scored on.
    """
    fractions = _draw_state_fractions(num_realizations, rng)

    if aggregated:
        immune, infected, exposed = (fractions[k] for k in ("immune", "infected", "exposed"))
        pop = state_population()[None, :]
    else:
        jitter = _draw_county_jitter(num_realizations, rng)
        of = state_of_county()
        immune, infected, exposed = (
            fractions[k][:, of] * jitter[k]
            for k in ("immune", "infected", "exposed")
        )
        pop = population()[None, :]

    R_0 = (immune * pop).astype(np.int64)
    I_0 = (infected * pop).astype(np.int64)
    E_0 = (exposed * pop).astype(np.int64)
    H_0 = np.rint(I_0 * GAMMA * HOSPITALIZATION_PROB * HOSPITAL_DAYS).astype(np.int64)
    D_0 = np.zeros_like(I_0)
    S_0 = pop - R_0 - I_0 - E_0 - H_0
    if not (S_0 > 0).all():
        raise ValueError("seed over-allocated some node's population")
    return np.stack([S_0, E_0, I_0, R_0, H_0, D_0], axis=2)


def county_initial_values(num_realizations: int, rng: np.random.Generator) -> np.ndarray:
    """Initial compartments for a model running on counties."""
    return _initial_values(num_realizations, rng, aggregated=False)


def state_initial_values(num_realizations: int, rng: np.random.Generator) -> np.ndarray:
    """Initial compartments for the model running on states."""
    return _initial_values(num_realizations, rng, aggregated=True)


# --- how each quantity is read out of a simulation result ---------------------

FORECAST_DAMPING = 1 / 28
FORECAST_SD_SCALE = 1.0
"""Multiple of the spread the filter is actually carrying."""
MINIMUM_FORECAST_SD = 0.01
"""A collapsed ensemble must not give a zero-variance forecast."""


@cache
def channels() -> tuple[Quantity, ...]:
    """Where the census and the deaths live in a result, and how a week of each forms.

    The census is a **stock**: its weekly value is the mean of the H compartment. Deaths
    are a **flow**: theirs is the sum of the H->D event. Summing a stock over seven days
    would multiply it by seven, so this dispatch is load-bearing, and it is the same rule
    the `ModelLink` uses (`agg(compartments="mean", events="sum")`).

    Indices are looked up by name rather than hardcoded, so reordering the IPM's
    compartments cannot silently repoint a channel.
    """
    ipm = SEIRHD()
    compartments = [str(c.name) for c in ipm.compartments]
    events = [str(e.name) for e in ipm.events]
    return (
        Quantity(
            name=QUANTITIES[0], source="compartments",
            index=compartments.index(CENSUS_COMPARTMENT), weekly="mean",
        ),
        Quantity(
            name=QUANTITIES[1], source="events",
            index=events.index(DEATHS_EVENT), weekly="sum",
        ),
    )


@cache
def scoring_groups() -> dict[str, list[int]]:
    """State FIPS -> the indices of the counties it covers, for the county models.

    The comparison is scored at the state scale, which the state model already runs at.
    Counties are summed **within each realization** before any quantile is taken, because
    quantiles do not add.
    """
    county_state = [node[:2] for node in scope().node_ids]
    groups = {
        state: [i for i, owner in enumerate(county_state) if owner == state]
        for state in state_scope().node_ids
    }
    covered = sum(len(members) for members in groups.values())
    if covered != scope().nodes:
        raise ValueError(
            f"{covered} of {scope().nodes} counties fall in a scored state"
        )
    return groups


def forecast_dynamics(
    filter_output, cholesky: dict[str, np.ndarray] | None = None
) -> dict[str, OrnsteinUhlenbeck | CorrelatedOU]:
    """OU dynamics for the horizon, re-derived from the filter at this origin.

    Both the centre and the spread come from the parameter's current ensemble rather than
    from the filtering constants, so the forecast propagates the uncertainty the filter
    actually has instead of the inflation it needed to stay healthy. Carrying that
    inflation in is a category error: the spread exists to fight assimilation-driven
    collapse, and nothing is assimilated in a forecast.

    `cholesky`, from `parameter_cholesky`, correlates the counties' shocks; without it
    each county's process is independent.
    """
    dynamics = {}
    for name in ("log_beta", "log_death_prob"):
        key = next(
            k for k in filter_output.estimated_params if str(k).endswith(name)
        )
        # (realizations, days, nodes) in LOG space; the last day is the origin.
        current = filter_output.estimated_params[key][:, -1, :]
        centre = float(np.mean(current))
        # Ensemble spread within a node, then the median across nodes: one node whose
        # ensemble has collapsed should not set the spread for every other node.
        carried = float(np.median(np.std(current, axis=0)))
        spread = max(FORECAST_SD_SCALE * carried, MINIMUM_FORECAST_SD)
        if cholesky is None:
            dynamics[f"ipm::{name}"] = OrnsteinUhlenbeck(
                damping=FORECAST_DAMPING, mean=centre, standard_deviation=spread,
            )
        else:
            dynamics[f"ipm::{name}"] = CorrelatedOU(
                damping=FORECAST_DAMPING, mean=centre, standard_deviation=spread,
                chol=cholesky[name],
            )
    return dynamics


def forecast_seed(seed: int, position: int) -> int:
    """A different forecast stream at each origin, matching `covid-v04.ipynb`.

    Demo 1 uses one stream for every origin, which correlates its forecast noise across
    origins. Demo 2 does not inherit that; see `refactor-plan-v01.md`.
    """
    return seed + 1 + position


def unknown_params(
    cholesky: dict[str, np.ndarray] | None = None,
) -> dict[str, UnknownParam]:
    """`beta` and `death_prob`, both per node, both Ornstein-Uhlenbeck.

    `Static()` dynamics collapse the severity ensemble to a log-sd of 0.020, which reads
    as certainty but is a filter that has stopped learning. Note `standard_deviation` is
    the stationary spread, not the per-step innovation.

    `cholesky`, from `parameter_cholesky`, correlates the counties' shocks while
    filtering; without it each county's process is independent.
    """
    log_beta = float(np.log(BETA))
    log_death_prob = float(np.log(DEATH_PROB))

    if cholesky is None:
        beta_dynamics = OrnsteinUhlenbeck(
            damping=BETA_DAMPING, mean=log_beta, standard_deviation=BETA_OU_SD
        )
        death_prob_dynamics = OrnsteinUhlenbeck(
            damping=DEATH_PROB_DAMPING, mean=log_death_prob,
            standard_deviation=DEATH_PROB_OU_SD,
        )
    else:
        beta_dynamics = CorrelatedOU(
            damping=BETA_DAMPING, mean=log_beta, standard_deviation=BETA_OU_SD,
            chol=cholesky["log_beta"],
        )
        death_prob_dynamics = CorrelatedOU(
            damping=DEATH_PROB_DAMPING, mean=log_death_prob,
            standard_deviation=DEATH_PROB_OU_SD, chol=cholesky["log_death_prob"],
        )

    return {
        "ipm::log_beta": UnknownParam(
            prior=GaussianPrior(mean=log_beta, standard_deviation=BETA_PRIOR_SD),
            dynamics=beta_dynamics,
        ),
        "ipm::log_death_prob": UnknownParam(
            prior=GaussianPrior(mean=log_death_prob,
                                standard_deviation=DEATH_PROB_PRIOR_SD),
            dynamics=death_prob_dynamics,
        ),
    }


def parameter_table() -> pd.DataFrame:
    """Every fixed parameter and its value (Pokutnaya element 6.1)."""
    rows = [
        ("sigma", f"{SIGMA:.6g}", "1/day", f"leaving latency, {LATENT_DAYS:g}-day mean"),
        ("gamma", f"{GAMMA:.6g}", "1/day", f"leaving infectiousness, {INFECTIOUS_DAYS:g} days"),
        ("xi", f"{XI:.6g}", "1/day", "waning, 1-year immunity"),
        ("hospitalization_duration", f"{HOSPITAL_DAYS:g}", "days",
         "measured: season patient-days / admissions = 6.97"),
        ("hospitalization_prob", f"{HOSPITALIZATION_PROB:g}", "-", "per infection"),
        ("death_prob", f"{DEATH_PROB:g}", "-",
         "deaths per hospitalization-equivalent; per-node deviation estimated"),
        ("beta", f"{BETA:g}", "1/day", f"prior median, implied R0 {BETA / GAMMA:.2f}"),
        ("immune_low", f"{LOWER_IMMUNE:g}", "-", "prior immunity, lower bound"),
        ("immune_high", f"{UPPER_IMMUNE:g}", "-", "prior immunity, upper bound"),
        ("county_jitter", f"{COUNTY_JITTER:g}", "-", "county variation around its state"),
        ("suppressed_lo", f"{SUPPRESSED_LO:g}", "deaths", "censoring interval, lower"),
        ("suppressed_hi", f"{SUPPRESSED_HI:g}", "deaths", "censoring interval, upper"),
        ("beta_prior_sd", f"{BETA_PRIOR_SD:g}", "log units", "prior sd of log beta"),
        ("beta_ou_sd", f"{BETA_OU_SD:g}", "log units", "stationary sd of log beta"),
        ("beta_damping", f"{BETA_DAMPING:.6g}", "1/day", "OU damping for log beta"),
        ("death_prob_prior_sd", f"{DEATH_PROB_PRIOR_SD:g}", "log units", ""),
        ("death_prob_ou_sd", f"{DEATH_PROB_OU_SD:g}", "log units", ""),
        ("death_prob_damping", f"{DEATH_PROB_DAMPING:.6g}", "1/day", ""),
    ]
    return pd.DataFrame(rows, columns=["parameter", "value", "unit", "description"])
