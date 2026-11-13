"""Data preparation for Demo 1 that is not epymorph: the frozen observations, severity,
the contact matrices and the initial conditions.

`demo-flu.ipynb` does everything that touches epymorph. What is here turns files and
random draws into the arrays it hands to epymorph, and every function takes plain arrays
and node IDs.

How the observations were fetched is in `scripts/fetch_flu_observations.py`, which no
build runs: the CSV is frozen evidence. Reasoning behind the values below is in the
maintainer's working folder: `demo-flu/contact-matrix-methods.md` (contact structure) and
`demo-flu/ihr-revision.md` (severity).
"""

import json
from hashlib import sha256
from pathlib import Path
from typing import NamedTuple, cast

import numpy as np
import pandas as pd
from epymorph.util import to_date_value_array

STRATA = ("age_00-04", "age_05-17", "age_18-49", "age_50-64", "age_65-74", "age_75-99")
"""The six age groups, as the observations name them."""
AGE_RANGES = ((0, 4), (5, 17), (18, 49), (50, 64), (65, 74), (75, None))
"""Each group's first and last year of age; None is open-ended."""

# --- the frozen observations ----------------------------------------------------------


class Observed(NamedTuple):
    """Weekly admissions, as arrays in the order of the nodes asked for."""

    by_age: np.ndarray
    """(weeks, nodes, groups)"""
    total: np.ndarray
    """(weeks, nodes), the sum of the groups: what every model is fitted and scored on."""
    dates: np.ndarray
    """(weeks,) week-ending dates."""
    by_age_source: np.ndarray
    """(weeks, nodes, groups) date-value pairs: what a stratified `Observations` takes."""
    total_source: np.ndarray
    """(weeks, nodes) date-value pairs: what the unstratified `Observations` takes."""


def load_observations(path: Path, nodes, start_date, weeks: int) -> Observed:
    """The frozen CDC admissions, one column per node in the order of `nodes`.

    Stops rather than guessing if the file does not cover the season: it is the target
    every model is scored against, and it is never refetched automatically.
    """
    table = pd.read_csv(path, dtype={"location": str}, parse_dates=["date"])

    stored = pd.to_datetime(sorted(table["date"].unique()))
    first, last = pd.Timestamp(start_date), pd.Timestamp(start_date) + pd.Timedelta(days=7 * (weeks - 1))
    if (stored.min(), stored.max(), len(stored)) != (first, last, weeks) or set(
        table["location"]
    ) != set(nodes):
        raise ValueError(
            f"{path} holds {len(stored)} weeks from {stored.min().date()} for "
            f"{table['location'].nunique()} jurisdictions; the season is {weeks} weeks "
            f"from {start_date} for {len(nodes)}. It is not refetched automatically."
        )

    dates = np.array(sorted(table["date"].unique()))
    pivot = table.pivot_table(
        index="date", columns=["location", "quantity"], values="value", aggfunc="first"
    )

    def one_group(name):
        return np.stack([pivot[(node, name)].to_numpy() for node in nodes], axis=1)

    by_age = np.stack([one_group(name) for name in STRATA], axis=2)
    total = by_age.sum(axis=2)
    week_dates = dates.astype("datetime64[D]")
    return Observed(
        by_age=by_age.astype(np.float64),
        total=total.astype(np.float64),
        dates=dates,
        by_age_source=to_date_value_array(week_dates, by_age.astype(np.int64)),
        total_source=to_date_value_array(week_dates, total.astype(np.int64)),
    )


def observation_table(path: Path) -> pd.DataFrame:
    """The frozen observations as a tidy table, with the scoring target added: `total`,
    the sum of the six groups (not CDC's own all-ages total, which is slightly larger)."""
    table = pd.read_csv(path, dtype={"location": str}, parse_dates=["date"])
    groups = table[table["quantity"].isin(STRATA)]
    total = (
        groups.groupby(["date", "location"], as_index=False)["value"].sum()
        .assign(quantity="total")
    )
    return pd.concat([table, total], ignore_index=True)


# --- severity -------------------------------------------------------------------------

SYMPTOMATIC_FRACTION = 2 / 3
"""Infections that become symptomatic; scales all six ratios below alike."""
CDC_CASE_HOSPITALIZATION_RATIO = {
    "00-04": 0.697 / 100,
    "05-17": 0.274 / 100,
    "18-49": 0.561 / 100,
    "50-64": 1.060 / 100,
    "65+": 9.09 / 100,
}
"""CDC burden-model symptomatic case-hospitalization ratios, the same in 2018-19 and
2019-20, so fixed age multipliers rather than one season's noise."""
ELDERLY_RATE_RATIO = 2.71
"""CDC reports one 65+ group; it is split by the observed 75+ to 65-74 admissions per
capita."""


def hospitalization_prob(population_by_age: dict[str, np.ndarray]) -> dict[str, float]:
    """The infection-hospitalization ratio of each group.

    `population_by_age` must be every jurisdiction's, not just the modelled ones': the 65+
    ratio is national, and splitting it by the modelled populations would make severity
    depend on which jurisdictions are in the comparison.
    """
    ratios = CDC_CASE_HOSPITALIZATION_RATIO
    elderly = population_by_age["age_65-74"].sum()
    oldest = population_by_age["age_75-99"].sum()
    # Population-weight the two elderly groups back to CDC's single 65+ ratio.
    elderly_base = ratios["65+"] * (elderly + oldest) / (elderly + ELDERLY_RATE_RATIO * oldest)
    values = [
        ratios["00-04"], ratios["05-17"], ratios["18-49"], ratios["50-64"],
        elderly_base, elderly_base * ELDERLY_RATE_RATIO,
    ]
    return {name: value * SYMPTOMATIC_FRACTION for name, value in zip(STRATA, values)}


def hospitalization_prob_total(prob: dict[str, float], population_by_age: dict[str, np.ndarray]) -> float:
    """The population-weighted average, so the unstratified model starts level."""
    weighted = sum(prob[name] * population_by_age[name].sum() for name in STRATA)
    total = sum(population_by_age[name].sum() for name in STRATA)
    return weighted / total


# --- contact matrices -----------------------------------------------------------------
#
# Mistry et al. (2021), Inferring high-resolution human mixing patterns for disease
# modeling, Nature Communications 12:323; Apache-2.0, github.com/mobs-lab/mixing-patterns.
# The national matrix and its age distribution are frozen in data/raw/mistry/ beside a
# provenance record holding their URL at a pinned commit and their checksum.


class SourceContacts(NamedTuple):
    """A contact matrix and the population it was measured in, which reciprocity
    (`C_ij * N_i == C_ji * N_j`) is defined against."""

    matrix: np.ndarray
    """`matrix[i, j]`: daily contacts of one person in group i with people in group j."""
    population: np.ndarray


def _frozen_mistry(path: Path) -> np.ndarray:
    data = path.read_bytes()
    record = json.loads(path.with_suffix(".provenance.json").read_text())
    if record["sha256"] != sha256(data).hexdigest():
        raise ValueError(f"{path} no longer matches its provenance record")
    return np.loadtxt(path, delimiter=",")


def mistry_contacts(mistry_dir: Path) -> SourceContacts:
    """The national contact matrix by single year of age (0 to 84+), from its frozen copy,
    collapsed onto the six groups."""
    stem = "United_States_country_level"
    matrix = _frozen_mistry(
        mistry_dir / f"contact_matrices_{stem}_M_overall_contact_matrix_85.csv"
    )
    population = _frozen_mistry(
        mistry_dir / f"age_distributions_{stem}_age_distribution_85.csv"
    )[:, 1]

    # Over the contactee (column) years, contacts add; over the contactor (row) years,
    # they are averaged, weighted by population.
    years = [np.arange(low, 84 + 1 if high is None else high + 1) for low, high in AGE_RANGES]
    populations = np.array([population[rows].sum() for rows in years])
    grouped = np.zeros((len(years), len(years)))
    for i, rows in enumerate(years):
        weights = population[rows] / population[rows].sum()
        for j, columns in enumerate(years):
            grouped[i, j] = weights @ matrix[np.ix_(rows, columns)].sum(axis=1)
    return SourceContacts(grouped, populations)


def _unit_spectral_radius(matrices: np.ndarray) -> np.ndarray:
    """Each node's matrix divided by its largest eigenvalue, so `q` means R0 * gamma in
    every node and every model: the models can differ in the shape of mixing only."""
    radii = np.array([float(np.max(np.abs(np.linalg.eigvals(m)))) for m in matrices])
    return matrices / radii[:, None, None]


def contact_matrices(source: SourceContacts, population_by_stratum, mixing: str) -> np.ndarray:
    """`(nodes, groups, groups)`: each node's contact matrix, for one mixing structure.

    `empirical` projects the measured matrix onto each node's own age distribution
    (Arregui et al. 2018, method 2: keep who people prefer to contact, substitute the
    target population's densities). `homogeneous` has no age preference: contact in
    proportion to each group's share of the population.
    """
    target = np.asarray(population_by_stratum, dtype=np.float64)
    if mixing == "homogeneous":
        shares = target / target.sum(axis=1, keepdims=True)
        return _unit_spectral_radius(np.repeat(shares[:, None, :], target.shape[1], axis=1))
    if mixing != "empirical":
        raise ValueError(f"unknown mixing {mixing!r}")
    density_ratio = (source.population.sum() * target) / (
        source.population[None, :] * target.sum(axis=1)[:, None]
    )
    return _unit_spectral_radius(source.matrix[None, :, :] * density_ratio[:, None, :])


# --- initial conditions ---------------------------------------------------------------

INFECTIOUS_DAYS = 5
SEED_LOG_SD = np.log(3) / 2
"""Two standard deviations span a factor of 3 either way."""
IMMUNE_LOW, IMMUNE_HIGH = 0.25, 0.60
UNOBSERVED_ADMISSIONS = 1.0
"""The detection floor: a group reporting no admissions in week 0 is seeded as if it had
this many."""
FLOORED_SPREAD_MULTIPLIER = 2.0
"""Extra spread for a group seeded from the floor."""


class Seeding(NamedTuple):
    fraction: np.ndarray
    """(nodes, groups) initial infectious fraction."""
    spread: np.ndarray
    """(nodes, groups) log-normal sd of that fraction."""


def seeding(week0_by_age: np.ndarray, prob: dict[str, float], population_by_stratum) -> Seeding:
    """The infectious fraction backed out of week-0 admissions through severity.

    Groups reporting no admissions are seeded from the detection floor instead, which is
    the same for every model, so all three start identically.
    """
    floored = week0_by_age < UNOBSERVED_ADMISSIONS
    admissions = np.maximum(week0_by_age, UNOBSERVED_ADMISSIONS)
    severity = np.array([prob[name] for name in STRATA])
    infections_that_week = admissions / severity[None, :]
    fraction = infections_that_week / 7 * INFECTIOUS_DAYS / population_by_stratum
    spread = np.where(floored, SEED_LOG_SD * FLOORED_SPREAD_MULTIPLIER, SEED_LOG_SD)
    return Seeding(fraction, spread)


def _node_generator(rng: np.random.Generator, node: str) -> np.random.Generator:
    """A random stream for one node, keyed by its FIPS code, so a node's draws depend only
    on the seed and on which node it is. `rng` must come straight from
    `np.random.default_rng(seed)`: its seed sequence is what is keyed."""
    parent = cast(np.random.SeedSequence, rng.bit_generator.seed_seq)
    child = np.random.SeedSequence(
        entropy=parent.entropy, spawn_key=(*parent.spawn_key, int(node))
    )
    return np.random.default_rng(child)


def initial_values(
    realizations: int,
    rng: np.random.Generator,
    *,
    nodes,
    seed: Seeding,
    population_by_stratum: np.ndarray,
    stratified: bool,
) -> np.ndarray:
    """`(realizations, nodes, compartments)` starting compartments: S, I, R, H for each
    group in turn, or once for the whole population when not `stratified`.

    Prior immunity is drawn per realization and held flat across groups: an age profile
    of immunity would be a second structural difference that could stand in for the
    contact matrix. The infectious fraction is log-normal around the seeding.
    """
    groups = len(STRATA) if stratified else 1
    values = np.zeros((realizations, len(nodes), groups * 4), dtype=np.int64)
    population_total = population_by_stratum.sum(axis=1)

    for n, node in enumerate(nodes):
        node_rng = _node_generator(rng, node)
        immune = node_rng.uniform(IMMUNE_LOW, IMMUNE_HIGH, size=realizations)
        for g in range(groups):
            if stratified:
                population = population_by_stratum[n, g]
                centre, log_sd = seed.fraction[n, g], seed.spread[n, g]
            else:
                population = population_total[n]
                centre, log_sd = seed.fraction[n].mean(), float(seed.spread[n].mean())

            spread = np.exp(log_sd * node_rng.standard_normal(realizations))
            infected = np.maximum(1, centre * spread * population).astype(np.int64)
            recovered = (immune * population).astype(np.int64)
            # The log-normal's upper tail can ask for more people than the group has left
            # after the immune; cap it there. It binds in no cell at this severity.
            infected = np.minimum(infected, population - recovered - 1)

            values[:, n, 4 * g + 0] = population - infected - recovered
            values[:, n, 4 * g + 1] = infected
            values[:, n, 4 * g + 2] = recovered

    if not (values[:, :, 0::4] > 0).all():
        raise ValueError("the initial conditions over-allocated some group's population")
    return values
