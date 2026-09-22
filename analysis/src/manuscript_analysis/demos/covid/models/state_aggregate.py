"""The state-resolution COVID model: three nodes, no spatial structure within a state.

The counties of `spatial_movement.py` are replaced by the three states they sum to. This
is the scale all three models are scored on, so this model is already there and the
county models must be aggregated to meet it.
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


def build() -> ForecastModel:
    scope = season.state_scope()
    rume = SingleStrataRUME.build(
        ipm=SEIRHD(),
        mm=mm.No(),
        init=Explicit(initials=np.zeros((scope.nodes, 6), dtype=np.int64)),
        scope=scope,
        time_frame=PlaceholderTimeFrame(),
        params={
            "ipm::beta": ExponentialTransform("log_beta"),
            "ipm::sigma": season.SIGMA,
            "ipm::gamma": season.GAMMA,
            "ipm::xi": season.XI,
            "ipm::hospitalization_prob": season.HOSPITALIZATION_PROB,
            "ipm::hospitalization_duration": season.HOSPITAL_DAYS,
            "ipm::death_prob": ExponentialTransform("log_death_prob"),
            "*::population": season.state_population(),
        },
    )

    observations = Observations(
        source=PlaceholderSource(),
        model_link=ModelLink(
            geo=rume.scope.select.all(),
            time=rume.time_frame.select.all().group(EveryNDays(7)).agg(
                compartments="mean", events="sum"
            ),
            quantity=rume.ipm.select.by(compartments="H", events="H->D"),
        ),
        likelihood=PoissonLikelihood(),
    )

    return ForecastModel(
        name="state",
        disease=season.season().disease,
        rume=rume,
        unknown_params=season.unknown_params(),
        observations=observations,
        quantities=season.QUANTITIES,
        observations_source=lambda: season.observation_source(aggregated=True),
        initial_values_factory=season.state_initial_values,
        channels=season.channels(),
        aggregate_quantities=False,
        # Already running at the scale everything is scored on, so no grouping.
        scoring_groups=None,
        forecast_dynamics=season.forecast_dynamics,
        forecast_seed=season.forecast_seed,
        movement_data_mode="home",
    )


model = build()
