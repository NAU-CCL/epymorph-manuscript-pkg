"""Data preparation for Demo 2 that is not epymorph: the frozen observations and the
initial conditions.

`demo-covid.ipynb` does everything that touches epymorph. What is here turns files and
random draws into the arrays it hands to epymorph. Every function takes plain arrays and
node IDs, so nothing here knows about scopes or ADRIOs.

How the observations were fetched and their suppressed deaths imputed is in
`scripts/fetch_covid_observations.py`, which no build runs: the CSV is frozen evidence.
"""

from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd
from epymorph.util import to_date_value_array

# --- the frozen observations --------------------------------------------------------


class Observed(NamedTuple):
    """Both observed quantities, as `(weeks, counties)` arrays."""

    census: np.ndarray
    """Mean daily hospital census: a stock."""
    deaths: np.ndarray
    """Weekly deaths, suppressed cells imputed: a flow."""
    suppressed: np.ndarray
    """True where CDC suppressed a death count of 1-9."""
    census_dates: np.ndarray
    death_dates: np.ndarray
    """The two quantities label the same MMWR week at opposite ends, six days apart."""


def load_observations(path: Path, counties, start_date, weeks: int) -> Observed:
    """The frozen CDC observations, one column per county in the order of `counties`.

    Stops rather than guessing if the file does not cover the season: it is the target
    every model is scored against, and it is never refetched automatically.
    """
    table = pd.read_csv(path, dtype={"location": str}, parse_dates=["date"])

    stored_weeks = table[table["quantity"] == "census"]["date"].nunique()
    first = table["date"].min().date()
    stored = set(table["location"].unique())
    if stored_weeks != weeks or first != start_date or stored != set(counties):
        raise ValueError(
            f"{path} holds {stored_weeks} weeks from {first} for {len(stored)} counties; "
            f"the season is {weeks} weeks from {start_date} for {len(counties)}. "
            "It is not refetched automatically: see scripts/fetch_covid_observations.py."
        )

    def one_quantity(name):
        part = table[table["quantity"] == name]
        dates = np.array(sorted(part["date"].unique()))
        pivot = part.pivot_table(index="date", columns="location", values="value")
        return np.stack([pivot[c].to_numpy() for c in counties], axis=1), dates

    census, census_dates = one_quantity("census")
    deaths, death_dates = one_quantity("deaths")
    flags = table[table["quantity"] == "deaths"].pivot_table(
        index="date", columns="location", values="suppressed"
    )
    suppressed = np.stack([flags[c].to_numpy() for c in counties], axis=1).astype(bool)
    return Observed(
        census, deaths, suppressed,
        census_dates.astype("datetime64[D]"), death_dates.astype("datetime64[D]"),
    )


def county_to_state(counties, states) -> np.ndarray:
    """`(states, counties)`, so `county_to_state @ values` sums each state's counties."""
    county_state = np.array([county[:2] for county in counties])
    matrix = np.zeros((len(states), len(counties)))
    for i, state in enumerate(states):
        matrix[i, county_state == state] = 1.0
    if not (matrix.sum(axis=0) == 1).all():
        raise ValueError("every county must belong to exactly one state")
    return matrix


def date_value_source(census, deaths, census_dates, death_dates) -> np.ndarray:
    """A `(weeks, nodes, 2)` date-value array, census then deaths: what epymorph's
    `Observations` takes as its source.

    Built one quantity at a time because the two carry different dates.
    """
    source = np.empty(
        (census.shape[0], census.shape[1], 2),
        dtype=to_date_value_array(census_dates[:1], census[:1, :1]).dtype,
    )
    source["date"][:, :, 0] = census_dates[:, None]
    source["date"][:, :, 1] = death_dates[:, None]
    source["value"][:, :, 0] = census
    source["value"][:, :, 1] = deaths
    return source


# --- initial conditions --------------------------------------------------------------

LOWER_IMMUNE, UPPER_IMMUNE = 0.05, 0.15
"""The fraction already immune when the season opens, drawn uniformly."""
LOWER_INFECTED, UPPER_INFECTED = 0.2 / 1000, 1.0 / 1000
"""The fraction infectious, and separately the fraction exposed, drawn uniformly."""
COUNTY_JITTER = 0.25
"""A county's fractions are its state's, times a uniform draw within this of 1."""

# Independent random streams, so a state's draw cannot collide with the draw for a county
# whose FIPS code happens to share its integer value.
STREAM_STATE_LEVEL = 0
STREAM_COUNTY_JITTER = 1


def _node_generator(rng: np.random.Generator, node: str, stream: int):
    """A random stream for one node, keyed by its FIPS code.

    A node's draws then depend only on the seed and on which node it is, not on how many
    other nodes there are or where it sits in the list. `rng` must come straight from
    `np.random.default_rng(seed)`: its seed sequence is what is keyed.
    """
    parent = rng.bit_generator.seed_seq
    child = np.random.SeedSequence(
        entropy=parent.entropy,
        spawn_key=(*parent.spawn_key, stream, int(node)),
    )
    return np.random.default_rng(child)


def _state_fractions(realizations: int, rng, states) -> dict[str, np.ndarray]:
    """One immune, infected and exposed fraction per state per realization.

    All three models draw these same values at a given seed, so their initial conditions
    agree at the state scale by construction. The draw order (immune, infected, exposed)
    is part of the result: change it and every number changes.
    """
    fractions = {
        name: np.zeros((realizations, len(states)))
        for name in ("immune", "infected", "exposed")
    }
    for index, state in enumerate(states):
        node_rng = _node_generator(rng, state, STREAM_STATE_LEVEL)
        fractions["immune"][:, index] = node_rng.uniform(
            LOWER_IMMUNE, UPPER_IMMUNE, size=realizations
        )
        fractions["infected"][:, index] = node_rng.uniform(
            LOWER_INFECTED, UPPER_INFECTED, size=realizations
        )
        fractions["exposed"][:, index] = node_rng.uniform(
            LOWER_INFECTED, UPPER_INFECTED, size=realizations
        )
    return fractions


def _county_jitter(realizations: int, rng, counties) -> dict[str, np.ndarray]:
    """One multiplicative jitter per county per realization, for each fraction."""
    jitter = {
        name: np.zeros((realizations, len(counties)))
        for name in ("immune", "infected", "exposed")
    }
    for index, county in enumerate(counties):
        node_rng = _node_generator(rng, county, STREAM_COUNTY_JITTER)
        for name in ("immune", "infected", "exposed"):
            jitter[name][:, index] = node_rng.uniform(
                1 - COUNTY_JITTER, 1 + COUNTY_JITTER, size=realizations
            )
    return jitter


def initial_values(
    realizations: int,
    rng: np.random.Generator,
    *,
    states,
    population: np.ndarray,
    gamma: float,
    hospitalization_prob: float,
    hospital_days: float,
    counties=None,
) -> np.ndarray:
    """`(realizations, nodes, 6)` starting compartments, in the order S E I R H D.

    The nodes are `states`, or `counties` when given, and `population` is per node.
    Counties within a state start from their state's fractions, jittered: they share an
    epidemic history, and drawing them independently would hand the county models far less
    uncertainty than the state model at the scale all three are scored on. The hospital
    starts at the census its infectious people would sustain.
    """
    fractions = _state_fractions(realizations, rng, states)
    if counties is None:
        immune, infected, exposed = (
            fractions[k] for k in ("immune", "infected", "exposed")
        )
    else:
        jitter = _county_jitter(realizations, rng, counties)
        state_of_county = np.argmax(county_to_state(counties, states), axis=0)
        immune, infected, exposed = (
            fractions[k][:, state_of_county] * jitter[k]
            for k in ("immune", "infected", "exposed")
        )
    pop = population[None, :]

    R_0 = (immune * pop).astype(np.int64)
    I_0 = (infected * pop).astype(np.int64)
    E_0 = (exposed * pop).astype(np.int64)
    H_0 = np.rint(I_0 * gamma * hospitalization_prob * hospital_days).astype(np.int64)
    D_0 = np.zeros_like(I_0)
    S_0 = pop - R_0 - I_0 - E_0 - H_0
    if not (S_0 > 0).all():
        raise ValueError("the initial conditions over-allocated some node's population")
    return np.stack([S_0, E_0, I_0, R_0, H_0, D_0], axis=2)


# --- the observations as tables, for scoring ---------------------------------------


def observation_tables(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The frozen observations as tidy tables, by county and summed to states.

    The two quantities label the same MMWR week at opposite ends: the census by its
    starting Sunday, deaths by its ending Saturday. The forecast files label every week
    the census's way, so the deaths are relabelled to match, week by week in order;
    otherwise they would join nothing. Both quantities sum across counties to a state.
    """
    table = pd.read_csv(path, dtype={"location": str}, parse_dates=["date"])

    weeks = {
        quantity: np.sort(part["date"].unique())
        for quantity, part in table.groupby("quantity")
    }
    if len({len(dates) for dates in weeks.values()}) != 1:
        raise ValueError("the two quantities cover different numbers of weeks")
    relabel = dict(zip(weeks["deaths"], weeks["census"]))
    by_county = table.copy()
    deaths = by_county["quantity"] == "deaths"
    by_county.loc[deaths, "date"] = by_county.loc[deaths, "date"].map(relabel)

    by_state = by_county.copy()
    by_state["location"] = by_state["location"].str[:2]
    by_state = by_state.groupby(["date", "location", "quantity"], as_index=False)["value"].sum()
    return by_county, by_state
