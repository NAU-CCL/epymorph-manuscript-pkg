"""Scoring quantile forecasts: the weighted interval score, coverage and relative WIS.

epymorph ships no scoring, so this is ours. It follows the forecasting hubs' conventions
(Bracher et al. 2021) and CDC's FluSight evaluations: scores on the log scale, and
relative WIS as a ratio of geometric means. Every function takes a forecast array whose
last axis is the quantile levels, and observations of the same leading shape.
"""

import numpy as np

HUB_QUANTILE_LEVELS = (
    0.010, 0.025, 0.050, 0.100, 0.150, 0.200, 0.250, 0.300, 0.350, 0.400, 0.450, 0.500,
    0.550, 0.600, 0.650, 0.700, 0.750, 0.800, 0.850, 0.900, 0.950, 0.975, 0.990,
)
"""The 23 levels FluSight and the COVID-19 hub collect, and that every run writes."""

SCORE_LEVELS = (0.025, 0.25, 0.5, 0.75, 0.975)
"""The levels every score is computed from: the median and the 50% and 95% intervals."""

SCALES = {"natural": None, "log": np.log1p}
"""The scales a forecast can be scored on. On the log scale, observations and forecast
quantiles are transformed by log(x + 1) before scoring, as FluSight does; the offset is
needed because some counts are zero. Transforming quantiles directly is legitimate because
the transform is increasing, and for the same reason it cannot change coverage."""

SCORE_LABELS = {"natural": "WIS", "log": "log WIS"}
HEADLINE_SCALE = "log"
"""The scale of every figure and headline table; the skill tables add the natural one."""


def weighted_interval_score(observed, forecasts, levels=SCORE_LEVELS, scale="natural"):
    """The weighted interval score of each forecast, on `scale`.

    `levels` must be sorted, symmetric about 0.5 and include it. Each central interval of
    nominal coverage 1 - alpha is weighted by alpha / 2 and the median's absolute error by
    1/2, normalized by the number of intervals plus 1/2 (Bracher et al. 2021).
    """
    levels = np.asarray(levels, dtype=np.float64)
    observed = np.asarray(observed, dtype=np.float64)
    forecasts = np.asarray(forecasts, dtype=np.float64)
    if SCALES[scale] is not None:
        observed, forecasts = SCALES[scale](observed), SCALES[scale](forecasts)

    median_index = int(np.flatnonzero(np.isclose(levels, 0.5))[0])
    median = forecasts[..., median_index]

    # Width, and the penalties for falling below or above, kept apart and added at the end.
    dispersion = np.zeros_like(observed)
    under = np.zeros_like(observed)
    over = np.zeros_like(observed)
    for k in range(median_index):
        alpha = 2.0 * levels[k]
        weight = alpha / 2.0
        lower, upper = forecasts[..., k], forecasts[..., -(k + 1)]
        dispersion += weight * (upper - lower)
        under += weight * ((2.0 / alpha) * np.maximum(observed - upper, 0.0))
        over += weight * ((2.0 / alpha) * np.maximum(lower - observed, 0.0))

    median_error = np.abs(observed - median)
    under += 0.5 * np.where(observed > median, median_error, 0.0)
    over += 0.5 * np.where(observed < median, median_error, 0.0)
    return 1.0 / (median_index + 0.5) * (dispersion + under + over)


def interval_coverage(observed, forecasts, levels, nominal: float) -> np.ndarray:
    """Whether each observation fell inside its central interval of coverage `nominal`."""
    levels = np.asarray(levels, dtype=np.float64)
    lower = int(np.flatnonzero(np.isclose(levels, (1.0 - nominal) / 2.0))[0])
    upper = int(np.flatnonzero(np.isclose(levels, 1.0 - (1.0 - nominal) / 2.0))[0])
    observed = np.asarray(observed, dtype=np.float64)
    forecasts = np.asarray(forecasts, dtype=np.float64)
    return (observed >= forecasts[..., lower]) & (observed <= forecasts[..., upper])


def relative_wis(scores, baseline, axis=None):
    """Relative WIS: the ratio of geometric mean scores, model over baseline.

    Below 1, the model is better. `axis` is what to average over; `None` pools
    everything. A score of exactly zero (a perfect forecast of a zero count) has no
    logarithm, so it is dropped together with its partner, keeping both averages over the
    same forecasts. Only a few county-week death counts are affected.
    """
    scores = np.asarray(scores, dtype=np.float64)
    baseline = np.asarray(baseline, dtype=np.float64)
    usable = (scores > 0) & (baseline > 0)
    log_ratio = np.log(np.where(usable, scores, 1.0)) - np.log(np.where(usable, baseline, 1.0))
    return np.exp(log_ratio.sum(axis=axis) / usable.sum(axis=axis))
