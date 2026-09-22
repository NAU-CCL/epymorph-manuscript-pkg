"""Everything the flu models share.

Every ingredient that is not the mixing structure lives here: scope, demography,
severity, observations and initial conditions. The model modules import from this and
add only what distinguishes them, so "the models differ by data, not by code" is
enforced by construction rather than by care.

Accessors are memoized, so importing all three model modules fetches once.

Reasoning behind the values below: `demo-flu/contact-matrix-methods.md` (contact
structure), `demo-flu/ihr-revision.md` (severity), `project-notes/handoff.md`
(seeding floor, ensemble size, eta damping).
"""

import os
from functools import cache
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd
from epymorph.adrio.acs5 import PopulationByAge, PopulationByAgeTable
from epymorph.adrio.cdc import CurrentStateAdmissions
from epymorph.forecasting.dynamic_params import GaussianPrior, OrnsteinUhlenbeck
from epymorph.forecasting.pipeline import UnknownParam
from epymorph.geography.us_census import StateScope
from epymorph.time import TimeFrame
from epymorph.util import to_date_value_array

from manuscript_analysis.demos.lib.contacts import (
    FLU_STRATA,
    SourceContacts,
    aggregate,
    fetch_source,
)
from manuscript_analysis.demos.lib.params.contact_wiring import (
    population_by_stratum_attribute,
)

from ... import paths
from ..seasons import ALL_STATES, FLU_2025, Season

SEASON = FLU_2025

DEMO_DIR = paths.RUNS / "flu"
"""Kept for callers that want the demo's output root; see `paths`."""
OBSERVATIONS_CSV = paths.observations("flu")

# --- strata -----------------------------------------------------------------

STRATA = tuple(band.name for band in FLU_STRATA)
NUM_STRATA = len(STRATA)
STRATA_LABELS = tuple(name.removeprefix("age_") for name in STRATA)
AGE_ENDPOINTS = dict(
    zip(STRATA, [(0, 4), (5, 17), (18, 49), (50, 64), (65, 74), (75, None)])
)
# The ADRIO's own age-group spellings, in the same order as STRATA.
DATA_AGE_GROUPS = ("0 to 4", "5 to 17", "18 to 49", "50 to 64", "65 to 74",
                   "75 and above")
# The ADRIO also publishes an all-ages total. It is NOT quite the sum of the six bands
# (about 0.25% larger), so it is stored for checking but never fitted; see `observations`.
REPORTED_TOTAL = "total_reported"

# --- natural history --------------------------------------------------------

GAMMA = 1 / 5.0
XI = 1 / 365
H_DURATION = 5.0
Q_MEAN = 0.25  # under unit-spectral-radius C, q = R0 * gamma

# --- severity ---------------------------------------------------------------

# Overridable so a sensitivity run can sit alongside the default one without editing
# the source: FLU_SYMPTOMATIC_FRACTION=0.45 python run_season.py ... -o output/...
# It scales all six IHRs by a common factor, which q(t) absorbs for the fit but not for
# the implied attack rate; see `ihr-revision.md` section 7.
SYMPTOMATIC_FRACTION = float(os.environ.get("FLU_SYMPTOMATIC_FRACTION") or 2 / 3)
# CDC burden model symptomatic case-hospitalization ratios, identical in 2018-19 and
# 2019-20, so these are fixed age multipliers rather than one season's noise.
CDC_CASE_HOSPITALIZATION_RATIO = {
    "00-04": 0.697 / 100,
    "05-17": 0.274 / 100,
    "18-49": 0.561 / 100,
    "50-64": 1.060 / 100,
    "65+": 9.09 / 100,
}
# CDC reports one 65+ group; split it by the observed admissions-per-capita ratio.
ELDERLY_RATE_RATIO = 2.71

# --- initial conditions -----------------------------------------------------

INFECTIOUS_DAYS = 5
SEED_LOG_SD = np.log(3) / 2  # 2 sd spans a factor of 3 either way
IMMUNE_LOW, IMMUNE_HIGH = 0.25, 0.60
UNOBSERVED_ADMISSIONS = 1.0  # the detection floor for zero-admission cells
FLOORED_SPREAD_MULTIPLIER = 2.0

# --- what the filter estimates ----------------------------------------------

LOG_Q_MEAN = float(np.log(Q_MEAN))
Q_PRIOR_SD = 0.15
Q_DAMPING = 1 / 35
Q_OU_SD = 0.15
# eta is a correction, not a free parameter, and the damping is what enforces that.
ETA_PRIOR_SD = 0.15
ETA_DAMPING = 1 / 10
ETA_OU_SD = 0.05


def season() -> Season:
    return SEASON


@cache
def scope() -> StateScope:
    return StateScope.in_states(list(SEASON.states), year=SEASON.acs_year)


@cache
def time_frame() -> TimeFrame:
    return TimeFrame.of(
        start_date=SEASON.start_date, duration_days=SEASON.duration_days
    )


@cache
def scored_locations() -> tuple[str, ...]:
    """FIPS codes of the jurisdictions the comparison is reported on.

    `Season.states` are postal abbreviations; every output file keys on FIPS, so the
    two must be translated before a filter can match.
    """
    scored = StateScope.in_states(list(SEASON.scored_states), year=SEASON.acs_year)
    return tuple(scored.node_ids)


@cache
def location_labels() -> dict[str, str]:
    """FIPS code to postal abbreviation, for labelling figures and tables."""
    return dict(zip(scope().node_ids, scope().labels))


class Demography(NamedTuple):
    by_stratum: np.ndarray
    """(N, A) population per node per stratum."""
    total: np.ndarray
    """(N,) population per node."""
    by_name: dict[str, np.ndarray]
    """(N,) population per node, keyed by stratum name."""


@cache
def demography() -> Demography:
    table = (
        PopulationByAgeTable()
        .with_context(scope=scope())
        .inspect()
        .result.astype(np.int64)
    )
    by_name = {
        name: PopulationByAge(*AGE_ENDPOINTS[name])
        .with_context(scope=scope(), params={"population_by_age_table": table})
        .inspect()
        .result
        for name in STRATA
    }
    by_stratum = np.stack([by_name[name] for name in STRATA], axis=1)
    return Demography(by_stratum, by_stratum.sum(axis=1), by_name)


@cache
def reference_demography() -> Demography:
    """Demography of every jurisdiction, regardless of which ones this season models.

    CDC's 65+ hospitalization ratio is a national figure, so splitting it between the
    two elderly bands must use a fixed reference age structure. Using the modelled
    scope's own populations would make severity, and through it the seeding, depend on
    which jurisdictions happen to be in the comparison.
    """
    reference_scope = StateScope.in_states(list(ALL_STATES), year=SEASON.acs_year)
    table = (
        PopulationByAgeTable()
        .with_context(scope=reference_scope)
        .inspect()
        .result.astype(np.int64)
    )
    by_name = {
        name: PopulationByAge(*AGE_ENDPOINTS[name])
        .with_context(scope=reference_scope,
                      params={"population_by_age_table": table})
        .inspect()
        .result
        for name in STRATA
    }
    by_stratum = np.stack([by_name[name] for name in STRATA], axis=1)
    return Demography(by_stratum, by_stratum.sum(axis=1), by_name)


@cache
def hospitalization_prob() -> dict[str, float]:
    """Infection-hospitalization ratio per stratum. See `ihr-revision.md`."""
    chr_by_age = CDC_CASE_HOSPITALIZATION_RATIO
    pops = reference_demography().by_name
    elderly = pops["age_65-74"].sum()
    oldest = pops["age_75-99"].sum()
    # Population-weight the two elderly bands back to CDC's single 65+ ratio.
    elderly_base = (
        chr_by_age["65+"]
        * (elderly + oldest)
        / (elderly + ELDERLY_RATE_RATIO * oldest)
    )
    values = [
        chr_by_age["00-04"],
        chr_by_age["05-17"],
        chr_by_age["18-49"],
        chr_by_age["50-64"],
        elderly_base,
        elderly_base * ELDERLY_RATE_RATIO,
    ]
    return {
        name: value * SYMPTOMATIC_FRACTION for name, value in zip(STRATA, values)
    }


@cache
def hospitalization_prob_total() -> float:
    """The population-weighted average, so the unstratified model starts level."""
    pops = demography().by_name
    weighted = sum(hospitalization_prob()[n] * pops[n].sum() for n in STRATA)
    return float(weighted / demography().total.sum())


@cache
def contact_source() -> SourceContacts:
    """The Mistry et al. national matrix, aggregated to the model's strata."""
    return aggregate(fetch_source("United_States"), FLU_STRATA)


def population_attribute():
    return population_by_stratum_attribute()


class Observed(NamedTuple):
    by_age: np.ndarray
    """(T, N, A) weekly admissions."""
    total: np.ndarray
    """(T, N) weekly admissions, summed over strata.

    Every model is fitted and scored on this, the stratified ones channel by channel
    and the unstratified one directly, so all three share an identical target.
    """
    total_reported: np.ndarray
    """(T, N) the ADRIO's own all-ages total, for checking only. Never fitted."""
    dates: np.ndarray
    """(T,) week-ending dates."""
    by_age_source: np.ndarray
    """(T, N, A) date-value pairs; what a stratified `Observations.source` takes."""
    total_source: np.ndarray
    """(T, N) date-value pairs; what the unstratified `Observations.source` takes."""


def fetch_observations(path: Path = OBSERVATIONS_CSV) -> Path:
    """Fetch weekly admissions from CDC and write them as a tidy CSV.

    Written once per season and shared by every model, so all models are scored
    against an identical, inspectable target. The CDC endpoint revises its counts,
    so this file is what makes a re-run reproducible.
    """
    context = {"scope": scope(), "time_frame": time_frame()}
    frames = []
    groups = [*zip(STRATA, DATA_AGE_GROUPS), (REPORTED_TOTAL, "Total")]
    for name, group in groups:
        result = (
            CurrentStateAdmissions(disease=SEASON.disease, age_group=group)
            .with_context(**context)
            .inspect()
            .result
        )
        for node, location in enumerate(scope().node_ids):
            frames.append(
                pd.DataFrame({
                    "date": result["date"][:, node],
                    "location": location,
                    "quantity": name,
                    "value": result["value"][:, node],
                })
            )
    table = pd.concat(frames, ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    table.sort_values(["date", "location", "quantity"]).to_csv(path, index=False)
    return path


@cache
def observations(path: Path = OBSERVATIONS_CSV) -> Observed:
    """Weekly admissions, loaded from the CSV, fetching it first if absent.

    The file is refetched if it does not cover the season window or the season's
    jurisdictions, so a changed season cannot be silently fitted to stale data.
    """
    if path.exists():
        stale = _observations_mismatch(path)
        if stale:
            print(f"refetching {path.name}: {stale}")
            path.unlink()
    if not path.exists():
        fetch_observations(path)
    table = pd.read_csv(path, dtype={"location": str}, parse_dates=["date"])

    dates = np.array(sorted(table["date"].unique()))
    locations = list(scope().node_ids)
    pivot = table.pivot_table(
        index="date", columns=["location", "quantity"], values="value", aggfunc="first"
    )
    def channel(name: str) -> np.ndarray:
        return np.stack([pivot[(loc, name)].to_numpy() for loc in locations], axis=1)

    by_age = np.stack([channel(name) for name in STRATA], axis=2)  # (T, N, A)
    total = by_age.sum(axis=2)
    # The filter wants date-value pairs at integer counts; scoring and plotting want
    # plain floats. Both come from the same arrays, so they cannot disagree.
    week_dates = dates.astype("datetime64[D]")
    return Observed(
        by_age=by_age.astype(np.float64),
        total=total.astype(np.float64),
        total_reported=channel(REPORTED_TOTAL).astype(np.float64),
        dates=dates,
        by_age_source=to_date_value_array(week_dates, by_age.astype(np.int64)),
        total_source=to_date_value_array(week_dates, total.astype(np.int64)),
    )


def _observations_mismatch(path: Path) -> str | None:
    """Why the stored observations do not match this season, or None if they do."""
    stored = pd.read_csv(path, dtype={"location": str}, parse_dates=["date"])
    weeks = pd.to_datetime(sorted(stored["date"].unique()))
    wanted_start = pd.Timestamp(SEASON.start_date)
    wanted_end = wanted_start + pd.Timedelta(days=7 * (SEASON.weeks - 1))
    if weeks.min() != wanted_start or weeks.max() != wanted_end:
        return (f"covers {weeks.min().date()}..{weeks.max().date()}, "
                f"season wants {wanted_start.date()}..{wanted_end.date()}")
    if len(weeks) != SEASON.weeks:
        return f"has {len(weeks)} weeks, season wants {SEASON.weeks}"
    stored_locations = set(stored["location"].unique())
    wanted = set(scope().node_ids)
    if stored_locations != wanted:
        return f"has {len(stored_locations)} locations, season wants {len(wanted)}"
    return None


class Seeding(NamedTuple):
    fraction: np.ndarray
    """(N, A) initial infected fraction."""
    spread: np.ndarray
    """(N, A) log-normal sd of that fraction."""
    was_floored: np.ndarray
    """(N, A) True where week-0 admissions were below the detection floor."""


@cache
def seeding() -> Seeding:
    """Initial prevalence backed out of week-0 admissions through the IHR.

    Cells reporting zero admissions are seeded from the detection floor instead,
    which is model-independent, so all models start identically.
    """
    week0 = observations().by_age[0]
    was_floored = week0 < UNOBSERVED_ADMISSIONS
    admissions = np.maximum(week0, UNOBSERVED_ADMISSIONS)
    severity = np.array([hospitalization_prob()[n] for n in STRATA])
    infections_that_week = admissions / severity[None, :]
    fraction = (
        infections_that_week / 7 * INFECTIOUS_DAYS / demography().by_stratum
    )
    spread = np.where(
        was_floored, SEED_LOG_SD * FLOORED_SPREAD_MULTIPLIER, SEED_LOG_SD
    )
    return Seeding(fraction, spread, was_floored)


def _node_generator(rng: np.random.Generator, location: str) -> np.random.Generator:
    """An independent stream for one node, keyed by its FIPS code.

    Drawing every node from one shared stream makes each node's values depend on how
    many other nodes there are and where it sits in the list, so adding a jurisdiction
    silently changes the initial conditions of every other one. Keying on the FIPS code
    instead means a node's draws depend only on the run seed and on which node it is.
    """
    parent = rng.bit_generator.seed_seq
    child = np.random.SeedSequence(
        entropy=parent.entropy,
        spawn_key=(*parent.spawn_key, int(location)),
    )
    return np.random.default_rng(child)


def _initial_values(
    num_realizations: int, rng: np.random.Generator, *, stratified: bool
) -> np.ndarray:
    num_compartments = 4  # S, I, R, H
    strata = NUM_STRATA if stratified else 1
    nodes = scope().nodes
    locations = list(scope().node_ids)
    seed = seeding()
    demo = demography()

    values = np.zeros(
        (num_realizations, nodes, strata * num_compartments), dtype=np.int64
    )

    for node in range(nodes):
        node_rng = _node_generator(rng, locations[node])
        # Prior immunity is drawn per realization but held flat across strata: an
        # age-varying immunity profile would be a second structural knob that could
        # substitute for the contact matrix.
        immune = node_rng.uniform(IMMUNE_LOW, IMMUNE_HIGH, size=num_realizations)

        for stratum in range(strata):
            if stratified:
                group_population = demo.by_stratum[node, stratum]
                centre = seed.fraction[node, stratum]
                log_sd = seed.spread[node, stratum]
            else:
                group_population = demo.total[node]
                centre = seed.fraction[node].mean()
                log_sd = float(seed.spread[node].mean())

            spread = np.exp(log_sd * node_rng.standard_normal(num_realizations))
            infected = np.maximum(1, centre * spread * group_population).astype(
                np.int64
            )
            recovered = (immune * group_population).astype(np.int64)

            # The seed is an unbounded log-normal, so its upper tail can ask for more
            # infected people than the group contains. Cap it at what is left after the
            # immune, which is a physical constraint rather than a tuning choice. It
            # binds only in the tail: at the default severity no cell is affected, and
            # at the lowest severity in the literature one cell in 31,200 is.
            headroom = group_population - recovered - 1
            infected = np.minimum(infected, headroom)

            offset = stratum * num_compartments
            values[:, node, offset + 0] = group_population - infected - recovered
            values[:, node, offset + 1] = infected
            values[:, node, offset + 2] = recovered

    # The seed is an unbounded log-normal, so a low enough IHR pushes prevalence past
    # the population and silently produces negative susceptibles. Fail loudly instead;
    # `demo-covid` has always had this check and this one did not.
    susceptible = values[:, :, 0::num_compartments]
    if not (susceptible > 0).all():
        worst = int(susceptible.min())
        bad = int((susceptible <= 0).sum())
        raise ValueError(
            f"seeding over-allocated {bad} of {susceptible.size} cells "
            f"(worst S = {worst:,}); the infected fraction has exceeded the "
            f"population. Check SYMPTOMATIC_FRACTION, currently "
            f"{SYMPTOMATIC_FRACTION:.4g}."
        )
    return values


def stratified_initial_values(
    num_realizations: int, rng: np.random.Generator
) -> np.ndarray:
    """`(R, N, A * 4)` initial compartments for a stratified model."""
    return _initial_values(num_realizations, rng, stratified=True)


def unstratified_initial_values(
    num_realizations: int, rng: np.random.Generator
) -> np.ndarray:
    """`(R, N, 4)` initial compartments for the unstratified model."""
    return _initial_values(num_realizations, rng, stratified=False)


def ou_unknown(
    mean: float, prior_sd: float, damping: float, ou_sd: float
) -> UnknownParam:
    """A log-space unknown: Gaussian prior, Ornstein-Uhlenbeck dynamics.

    OU rather than static because a static parameter suffers EnKF spread collapse.
    """
    return UnknownParam(
        prior=GaussianPrior(mean=mean, standard_deviation=prior_sd),
        dynamics=OrnsteinUhlenbeck(
            damping=damping, mean=mean, standard_deviation=ou_sd
        ),
    )


def unknown_params(*, stratified: bool) -> dict[str, UnknownParam]:
    """`q` for every model, plus one `eta` correction per stratum when stratified."""
    q_key = "meta::ipm::log_q" if stratified else "ipm::log_q"
    unknowns = {q_key: ou_unknown(LOG_Q_MEAN, Q_PRIOR_SD, Q_DAMPING, Q_OU_SD)}
    if stratified:
        # Centred on zero: eta corrects C, it does not carry the level, which is q's job.
        for i in range(NUM_STRATA):
            unknowns[f"meta::ipm::log_eta_{i}"] = ou_unknown(
                0.0, ETA_PRIOR_SD, ETA_DAMPING, ETA_OU_SD
            )
    return unknowns


def parameter_table() -> pd.DataFrame:
    """Every fixed parameter and its value (Pokutnaya element 6.1)."""
    rows = [
        ("gamma", f"{GAMMA:.6g}", "1/day", "recovery rate, 5-day infectious period"),
        ("xi", f"{XI:.6g}", "1/day", "waning rate, 1-year immunity"),
        ("hospitalization_duration", f"{H_DURATION:g}", "days", "mean stay"),
        ("q_mean", f"{Q_MEAN:g}", "1/day", "prior mean transmissibility, R0 * gamma"),
        ("symptomatic_fraction", f"{SYMPTOMATIC_FRACTION:.4g}", "-",
         "infections that become symptomatic"),
        ("elderly_rate_ratio", f"{ELDERLY_RATE_RATIO:g}", "-",
         "75+ to 65-74 admissions per capita"),
        ("infectious_days", f"{INFECTIOUS_DAYS:g}", "days", "seeding window"),
        ("seed_log_sd", f"{SEED_LOG_SD:.4g}", "log units", "seed spread"),
        ("floored_spread_multiplier", f"{FLOORED_SPREAD_MULTIPLIER:g}", "-",
         "extra seed spread where week-0 admissions were floored"),
        ("immune_low", f"{IMMUNE_LOW:g}", "-", "prior immunity, lower bound"),
        ("immune_high", f"{IMMUNE_HIGH:g}", "-", "prior immunity, upper bound"),
        ("unobserved_admissions", f"{UNOBSERVED_ADMISSIONS:g}", "admissions",
         "detection floor for zero-admission cells"),
        ("q_prior_sd", f"{Q_PRIOR_SD:g}", "log units", "prior sd of log q"),
        ("q_damping", f"{Q_DAMPING:.6g}", "1/day", "OU damping for log q"),
        ("q_ou_sd", f"{Q_OU_SD:g}", "log units", "OU sd for log q"),
        ("eta_prior_sd", f"{ETA_PRIOR_SD:g}", "log units", "prior sd of log eta"),
        ("eta_damping", f"{ETA_DAMPING:.6g}", "1/day", "OU damping for log eta"),
        ("eta_ou_sd", f"{ETA_OU_SD:g}", "log units", "OU sd for log eta"),
    ]
    for name in STRATA:
        rows.append(
            (f"hospitalization_prob[{name.removeprefix('age_')}]",
             f"{hospitalization_prob()[name]:.6g}", "-",
             "infection-hospitalization ratio")
        )
    rows.append(
        ("hospitalization_prob[total]", f"{hospitalization_prob_total():.6g}", "-",
         "population-weighted, unstratified model")
    )
    return pd.DataFrame(rows, columns=["parameter", "value", "unit", "description"])
