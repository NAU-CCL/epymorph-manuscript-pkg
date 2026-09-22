"""Age-stratified flu models, which differ only in their mixing structure.

Both models here have six age strata, the same demography, severity, seeding and
priors. The single argument `mixing` selects the contact matrix:

- `empirical`: the Mistry et al. matrix, projected onto this demography.
- `homogeneous`: no age preference, contact in proportion to group size.

They are one module rather than two because that difference is one argument. Adding
`within_group`, or per-state source matrices, is one more line here.

Compare with `single_strata.py`, which has no age structure at all.
"""

import epymorph.initializer as init
import numpy as np
from epymorph.data import ipm, mm
from epymorph.forecasting.dynamic_params import ExponentialTransform
from epymorph.forecasting.filter import ModelLink, Observations
from epymorph.forecasting.likelihood import PoissonLikelihood
from epymorph.rume import GPM
from epymorph.time import EveryNDays

from manuscript_analysis.demos.lib.forecasting import (
    ForecastModel,
    PlaceholderSource,
    PlaceholderTimeFrame,
)
from manuscript_analysis.demos.lib.ipms.flu_age_mixing import age_mixing_rume_builder
from manuscript_analysis.demos.lib.params.contact_wiring import contact_params

from . import flu_season as season

SEED_RATIOS = np.array([900, 1, 200, 0], dtype=np.int64)  # S, I, R, H

FluRUME = age_mixing_rume_builder([
    GPM(
        name=name,
        ipm=ipm.SIRH(),
        mm=mm.No(),
        init=init.Proportional(ratios=SEED_RATIOS),
    )
    for name in season.STRATA
])


def build(mixing: str) -> ForecastModel:
    """One stratified model. `mixing` is the only thing that varies."""
    rume = FluRUME().build(
        scope=season.scope(),
        time_frame=PlaceholderTimeFrame(),
        params={
            # meta_edges owns all transmission, so the base IPM must not add any.
            "*::ipm::beta": 0.0,
            "*::ipm::gamma": season.GAMMA,
            "*::ipm::xi": season.XI,
            "*::ipm::hospitalization_duration": season.H_DURATION,
            "meta::ipm::q": ExponentialTransform("log_q"),
            "meta::ipm::population_by_stratum": season.demography().by_stratum,
            **{
                f"gpm:{name}::*::population": season.demography().by_name[name]
                for name in season.STRATA
            },
            **{
                f"gpm:{name}::ipm::hospitalization_prob": (
                    season.hospitalization_prob()[name]
                )
                for name in season.STRATA
            },
            **{
                f"meta::ipm::eta_{i}": ExponentialTransform(f"log_eta_{i}")
                for i in range(season.NUM_STRATA)
            },
            **contact_params(
                season.contact_source(),
                mixing=mixing,
                population_attribute=season.population_attribute(),
            ),
        },
    )

    observations = Observations(
        source=PlaceholderSource(),
        model_link=ModelLink(
            geo=rume.scope.select.all(),
            time=rume.time_frame.select.all().group(EveryNDays(7)).agg("sum"),
            # Ungrouped: one observation channel per stratum, matching the data.
            quantity=rume.ipm.select.events("I_*->H_*"),
        ),
        likelihood=PoissonLikelihood(),
    )

    return ForecastModel(
        name=f"multi-strata-{mixing}",
        disease=season.season().disease,
        rume=rume,
        unknown_params=season.unknown_params(stratified=True),
        observations=observations,
        quantities=season.STRATA,
        observations_source=lambda: season.observations().by_age_source,
        initial_values_factory=season.stratified_initial_values,
    )


empirical = build("empirical")
homogeneous = build("homogeneous")
