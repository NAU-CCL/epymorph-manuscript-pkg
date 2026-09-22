"""County-resolution COVID models, which differ only in whether people move.

Both run on 32 counties with the same demography, severity, seeding and priors. The
single argument selects the movement model:

- `movement`: commuting flows from ACS (`mm.Pei()`).
- `county`: no movement at all (`mm.No()`), so counties are independent.

They are one module rather than two because that difference is one argument. Compare with
`state_aggregate.py`, which removes the spatial resolution instead.
"""

import numpy as np
from epymorph.data import mm
from epymorph.forecasting.dynamic_params import ExponentialTransform
from epymorph.forecasting.filter import ModelLink, Observations
from epymorph.forecasting.likelihood import PoissonLikelihood
from epymorph.initializer import Explicit
from epymorph.rume import SingleStrataRUME
from epymorph.time import EveryNDays

from manuscript_analysis.demos.lib.forecasting import (
    ForecastModel,
    PlaceholderSource,
    PlaceholderTimeFrame,
)
from manuscript_analysis.demos.lib.ipms.covid_seirhd import SEIRHD

from . import covid_season as season


def build(movement: bool) -> ForecastModel:
    """One county-resolution model. Movement is the only thing that varies."""
    scope = season.scope()
    params = {
        "ipm::beta": ExponentialTransform("log_beta"),
        "ipm::sigma": season.SIGMA,
        "ipm::gamma": season.GAMMA,
        "ipm::xi": season.XI,
        "ipm::hospitalization_prob": season.HOSPITALIZATION_PROB,
        "ipm::hospitalization_duration": season.HOSPITAL_DAYS,
        "ipm::death_prob": ExponentialTransform("log_death_prob"),
        "*::population": season.population(),
    }
    if movement:
        params["mm::commuters"] = season.commuters()

    rume = SingleStrataRUME.build(
        ipm=SEIRHD(),
        mm=mm.Pei() if movement else mm.No(),
        # Initial values are handed to the filter directly; this is a placeholder.
        init=Explicit(initials=np.zeros((scope.nodes, 6), dtype=np.int64)),
        scope=scope,
        time_frame=PlaceholderTimeFrame(),
        params=params,
    )

    observations = Observations(
        source=PlaceholderSource(),
        model_link=ModelLink(
            geo=rume.scope.select.all(),
            # A census is a stock and deaths are a flow, so the weekly aggregation
            # dispatches by type: mean of the compartment, sum of the event.
            time=rume.time_frame.select.all().group(EveryNDays(7)).agg(
                compartments="mean", events="sum"
            ),
            quantity=rume.ipm.select.by(compartments="H", events="H->D"),
        ),
        likelihood=PoissonLikelihood(),
    )

    return ForecastModel(
        name="movement" if movement else "county",
        disease=season.season().disease,
        rume=rume,
        unknown_params=season.unknown_params(),
        observations=observations,
        quantities=season.QUANTITIES,
        observations_source=lambda: season.observation_source(aggregated=False),
        initial_values_factory=season.county_initial_values,
        channels=season.channels(),
        # A census and a death count do not add, so there is no "total" quantity here.
        aggregate_quantities=False,
        # 32 counties are scored as the 3 states the state model runs at.
        scoring_groups=season.scoring_groups(),
        forecast_dynamics=season.forecast_dynamics,
        forecast_seed=season.forecast_seed,
        movement_data_mode="home",
    )


movement = build(True)
county = build(False)
