"""The unstratified flu model: one population, no age structure.

`C = [1]`, so `beta` and `q` coincide. Its single severity value is the
population-weighted average of the six, so it starts at the same level as the
stratified models in `multi_strata_flu.py`.
"""

import epymorph.initializer as init
import numpy as np
from epymorph.data import ipm, mm
from epymorph.forecasting.dynamic_params import ExponentialTransform
from epymorph.forecasting.filter import ModelLink, Observations
from epymorph.forecasting.likelihood import PoissonLikelihood
from epymorph.rume import SingleStrataRUME
from epymorph.time import EveryNDays

from manuscript_analysis.demos.lib.forecasting import (
    TOTAL_QUANTITY,
    ForecastModel,
    PlaceholderSource,
    PlaceholderTimeFrame,
)

from . import flu_season as season

SEED_RATIOS = np.array([900, 1, 200, 0], dtype=np.int64)  # S, I, R, H


def build() -> ForecastModel:
    rume = SingleStrataRUME.build(
        ipm=ipm.SIRH(),
        mm=mm.No(),
        init=init.Proportional(ratios=SEED_RATIOS),
        scope=season.scope(),
        time_frame=PlaceholderTimeFrame(),
        params={
            "ipm::beta": ExponentialTransform("log_q"),  # C = [1], so beta == q
            "ipm::gamma": season.GAMMA,
            "ipm::xi": season.XI,
            "ipm::hospitalization_prob": season.hospitalization_prob_total(),
            "ipm::hospitalization_duration": season.H_DURATION,
            "*::population": season.demography().total,
        },
    )

    observations = Observations(
        source=PlaceholderSource(),
        model_link=ModelLink(
            geo=rume.scope.select.all(),
            time=rume.time_frame.select.all().group(EveryNDays(7)).agg("sum"),
            quantity=rume.ipm.select.events("I->H"),
        ),
        likelihood=PoissonLikelihood(),
    )

    return ForecastModel(
        name="single-strata",
        disease=season.season().disease,
        rume=rume,
        unknown_params=season.unknown_params(stratified=False),
        observations=observations,
        quantities=(TOTAL_QUANTITY,),
        observations_source=lambda: season.observations().total_source,
        initial_values_factory=season.unstratified_initial_values,
    )


model = build()
