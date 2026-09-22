"""Forecasting seasons, kept separate from the models.

The analogue of `../FluSight-pipeline/challenges.py`: a season says *what* is being
forecast and over what window, never *how*.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from manuscript_analysis.demos.lib.forecasting import Disease

# Every state plus DC and Puerto Rico, as FluSight requires.
ALL_STATES = (
    "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "HI", "IA",
    "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN", "MO", "MS",
    "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA",
    "PR", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY",
)

# Puerto Rico is forecast but excluded from the model comparison: its influenza
# seasonality is tropical rather than temperate, so the single winter peak these
# models assume does not describe it. FluSight scores the same way.
UNSCORED_STATES = ("PR",)


@dataclass(frozen=True)
class Season:
    """One forecasting season."""

    name: str

    disease: Disease

    start_date: date
    """First day of the **simulated** window, which is the first burn-in week.

    Note this differs from `../FluSight-pipeline/challenges.py`, where a challenge's
    dates are the *forecast* window and the runner extends backwards by the burn-in.
    Here the burn-in is inside the window, so the first forecast lands
    `burn_in_weeks` after this date.
    """

    weeks: int
    """Length of the simulated window in weeks, burn-in included."""

    states: tuple[str, ...]
    """Jurisdictions to forecast."""

    acs_year: int
    """ACS 5-year vintage for the demography; must be a supported data year."""

    observations_file: str = "output/observations.csv"
    """Where this season's observations are frozen, relative to the demo directory."""

    burn_in_weeks: int = 4
    """Weeks assimilated before the first forecast. The CLI can override."""

    horizon_weeks: int = 4
    """Forecast horizon. The CLI can override."""

    @property
    def duration_days(self) -> int:
        return 7 * self.weeks

    @property
    def scored_states(self) -> tuple[str, ...]:
        """The jurisdictions the model comparison is reported on."""
        return tuple(s for s in self.states if s not in UNSCORED_STATES)


seasons: Mapping[str, Season] = {}

# The full FluSight 2025-26 challenge period. The challenge runs 2025-11-19 to
# 2026-05-27, which in the CDC data's week-ending-Saturday labels is 2025-11-22 to
# 2026-05-30. Ten burn-in weeks precede the first origin, matching FluSight's default,
# so the simulated window opens on 2025-09-13.
#
# Forecasting the whole challenge period matters: the season peaks on 2026-01-03 and
# then declines for eleven weeks, and an earlier window that stopped in March cut the
# decline off entirely.
FLU_2025 = Season(
    name="FLU2025",
    disease="Influenza",
    start_date=date.fromisoformat("2025-09-13"),
    weeks=38,
    states=ALL_STATES,
    acs_year=2024,
    burn_in_weeks=10,
)
seasons[FLU_2025.name] = FLU_2025
