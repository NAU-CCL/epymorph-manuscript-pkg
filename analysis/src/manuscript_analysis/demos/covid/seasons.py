"""Forecasting seasons for the COVID demo.

Each demo defines its own `Season`; `manuscript_analysis.demos.lib.cli` only requires the handful of fields in
its `SeasonLike` protocol (name, disease, start_date, weeks, burn_in_weeks,
horizon_weeks). Everything else here is COVID-specific and the runner never sees it.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from manuscript_analysis.demos.lib.forecasting import Disease

STATES = ("MA", "CT", "NH")
"""The region. See `project-notes/handoff.md` for why it moved here from Four Corners."""


@dataclass(frozen=True)
class Season:
    """One forecasting season."""

    name: str
    disease: Disease

    start_date: date
    """First day of the simulated window, which is the first burn-in week.

    **Must be a Sunday.** `CountyDeaths` labels an MMWR week by its ending Saturday and
    `COVIDFacilityHospitalization` by its starting Sunday, so a Saturday start puts the
    two quantities a full week apart and the deaths run ahead of the model all season.
    """

    weeks: int
    states: tuple[str, ...]

    census_year: int
    """Census vintage for the county and state geography."""

    cdc_year: int
    """County vintage the CDC datasets are keyed on; checked against `census_year`."""

    observations_file: str = "output/observations.csv"
    burn_in_weeks: int = 8
    horizon_weeks: int = 4

    def __post_init__(self):
        if self.start_date.weekday() != 6:
            raise ValueError(
                f"{self.name} starts on a {self.start_date:%A}; MMWR weeks require a "
                "Sunday or the two observed quantities are a week apart"
            )


seasons: Mapping[str, Season] = {}

COVID_2020 = Season(
    name="COVID2020",
    disease="Covid",
    # The simulated window opens EIGHT WEEKS BEFORE the period being forecast, so the
    # burn-in runs on pre-wave data instead of eating the autumn rise. It previously
    # opened 2020-10-04, which put the first forecast origin at 2020-11-29 and discarded
    # the most informative eight weeks of the season. Now the first origin IS 2020-10-04.
    # Demo 1 made exactly this correction; see its `refactor-plan-v01.md` phase 4.5.
    #
    # Still a Sunday, which `__post_init__` enforces: the two ADRIOs label an MMWR week at
    # opposite ends, so a Saturday start puts the quantities a week apart.
    start_date=date.fromisoformat("2020-08-09"),
    weeks=35,
    states=STATES,
    census_year=2015,
    cdc_year=2019,
)
seasons[COVID_2020.name] = COVID_2020
