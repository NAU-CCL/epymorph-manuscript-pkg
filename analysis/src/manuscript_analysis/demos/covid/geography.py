"""The COVID demo's geography, population and commuting, for `evaluation.py`.

TEMPORARY (restructure step 4): `demo-covid.ipynb` now builds the models and reads these
same frozen inputs itself. This module keeps `evaluation.py`, the exporter and the tables
working until step 5 moves the evaluation into the notebook, which then hands the figures
what they need. Delete it then.
"""

from datetime import date
from functools import cache

import numpy as np
from epymorph.adrio.acs5 import Population
from epymorph.adrio.commuting_flows import Commuters
from epymorph.geography.us_census import CountyScope, StateScope
from epymorph.time import TimeFrame

from manuscript_analysis.data import ProvenanceCachedADRIO

from .. import paths

STATES = ["MA", "CT", "NH"]
CENSUS_YEAR = 2015
SEASON = TimeFrame.of(start_date=date(2020, 8, 9), duration_days=7 * 35)


@cache
def scope() -> CountyScope:
    return CountyScope.in_states(STATES, year=CENSUS_YEAR)


@cache
def state_scope() -> StateScope:
    return StateScope.in_states(STATES, year=CENSUS_YEAR)


def _frozen(adrio, name: str, what: str) -> ProvenanceCachedADRIO:
    return ProvenanceCachedADRIO(
        adrio,
        cache_path=paths.RAW / f"covid-{name}-{CENSUS_YEAR}-{'-'.join(STATES).lower()}.npz",
        description=f"{what}; {CENSUS_YEAR} vintage; {', '.join(STATES)}",
    )


@cache
def population() -> np.ndarray:
    return (
        _frozen(Population(), "population-counties", "ACS 5-year population per county")
        .with_context(scope=scope(), time_frame=SEASON)
        .inspect().result.astype(np.int64)
    )


@cache
def commuters() -> np.ndarray:
    return np.asarray(
        _frozen(Commuters(), "commuters-counties", "ACS commuting flows between counties")
        .with_context(scope=scope(), time_frame=SEASON)
        .inspect().result
    ).astype(np.int64)
