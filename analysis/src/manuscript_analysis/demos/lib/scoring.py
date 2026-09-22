"""Forecast scoring. epymorph ships no scoring code, so this is written by hand.

Everything here operates on *quantile forecasts*: an array whose last axis runs
over quantile levels, paired with an array of observations of the same leading
shape. All functions are pure numpy and broadcast over any leading axes
(typically time x node, or time x node x quantity).

Scoring convention follows the US forecasting hubs (Bracher et al. 2021):
the weighted interval score (WIS) approximates CRPS as the number of central
intervals grows, and decomposes into dispersion, underprediction and
overprediction components.
"""

from collections.abc import Sequence
from typing import NamedTuple

import numpy as np

# The 23-level grid used by the COVID-19 and FluSight forecast hubs.
HUB_QUANTILE_LEVELS = (
    0.010,
    0.025,
    0.050,
    0.100,
    0.150,
    0.200,
    0.250,
    0.300,
    0.350,
    0.400,
    0.450,
    0.500,
    0.550,
    0.600,
    0.650,
    0.700,
    0.750,
    0.800,
    0.850,
    0.900,
    0.950,
    0.975,
    0.990,
)

# The five levels the existing demo notebooks already compute.
DEMO_QUANTILE_LEVELS = (0.025, 0.25, 0.5, 0.75, 0.975)


class WIS(NamedTuple):
    """A weighted interval score and its three additive components.

    ``total`` equals ``dispersion + underprediction + overprediction``.
    """

    total: np.ndarray
    dispersion: np.ndarray
    underprediction: np.ndarray
    overprediction: np.ndarray


def _check_levels(quantile_levels: Sequence[float]) -> np.ndarray:
    """Validate that the levels are sorted, unique, and symmetric about 0.5."""
    levels = np.asarray(quantile_levels, dtype=np.float64)
    if levels.ndim != 1:
        raise ValueError("quantile_levels must be one-dimensional")
    if not np.all(np.diff(levels) > 0):
        raise ValueError("quantile_levels must be strictly increasing")
    if not np.isclose(levels, 0.5).any():
        raise ValueError("quantile_levels must include the median (0.5)")
    if not np.allclose(levels, 1.0 - levels[::-1]):
        raise ValueError("quantile_levels must be symmetric about 0.5")
    return levels


def interval_score(
    observations: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    alpha: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Score a single central prediction interval of nominal coverage 1 - alpha.

    Returns
    -------
    :
        The dispersion, underprediction, and overprediction components. Their
        sum is the interval score.
    """
    dispersion = upper - lower
    # The forecast was too low: the observation fell above the interval.
    underprediction = (2.0 / alpha) * np.maximum(observations - upper, 0.0)
    # The forecast was too high: the observation fell below the interval.
    overprediction = (2.0 / alpha) * np.maximum(lower - observations, 0.0)
    return dispersion, underprediction, overprediction


def weighted_interval_score(
    observations: np.ndarray,
    forecasts: np.ndarray,
    quantile_levels: Sequence[float] = DEMO_QUANTILE_LEVELS,
) -> WIS:
    """Compute the weighted interval score for a quantile forecast.

    Parameters
    ----------
    observations :
        Observed values, shape ``(...)``.
    forecasts :
        Predicted quantiles, shape ``(..., len(quantile_levels))``, with the
        last axis in increasing level order.
    quantile_levels :
        The quantile levels, sorted, symmetric about 0.5, and including 0.5.

    Returns
    -------
    :
        The score and its components, each of shape ``(...)``.
    """
    levels = _check_levels(quantile_levels)
    observations = np.asarray(observations, dtype=np.float64)
    forecasts = np.asarray(forecasts, dtype=np.float64)

    if forecasts.shape[-1] != levels.size:
        raise ValueError(
            f"forecasts last axis is {forecasts.shape[-1]}, "
            f"expected {levels.size} to match quantile_levels"
        )
    if forecasts.shape[:-1] != observations.shape:
        raise ValueError(
            f"forecasts leading shape {forecasts.shape[:-1]} does not match "
            f"observations shape {observations.shape}"
        )

    median_index = int(np.flatnonzero(np.isclose(levels, 0.5))[0])
    median = forecasts[..., median_index]

    # Weight the absolute error of the median by 1/2, and each central interval
    # of nominal coverage 1 - alpha by alpha/2.
    dispersion = np.zeros_like(observations, dtype=np.float64)
    under = np.zeros_like(observations, dtype=np.float64)
    over = np.zeros_like(observations, dtype=np.float64)
    num_intervals = median_index
    for k in range(num_intervals):
        alpha = 2.0 * levels[k]
        weight = alpha / 2.0
        d, u, o = interval_score(
            observations,
            lower=forecasts[..., k],
            upper=forecasts[..., -(k + 1)],
            alpha=alpha,
        )
        dispersion += weight * d
        under += weight * u
        over += weight * o

    # The median term is conventionally booked as dispersion-free absolute
    # error; split it into the same over/under directions for a clean
    # three-way decomposition that still sums to the total.
    median_error = np.abs(observations - median)
    under += 0.5 * np.where(observations > median, median_error, 0.0)
    over += 0.5 * np.where(observations < median, median_error, 0.0)

    # Bracher et al.'s normalization: K central intervals plus the median term.
    scale = 1.0 / (num_intervals + 0.5)
    return WIS(
        total=scale * (dispersion + under + over),
        dispersion=scale * dispersion,
        underprediction=scale * under,
        overprediction=scale * over,
    )


def interval_coverage(
    observations: np.ndarray,
    forecasts: np.ndarray,
    quantile_levels: Sequence[float],
    nominal: float,
) -> np.ndarray:
    """Indicate whether each observation fell inside its central interval.

    Parameters
    ----------
    nominal :
        Nominal coverage of the central interval, e.g. ``0.95``.

    Returns
    -------
    :
        A boolean array of shape ``(...)``. Average it over whatever axes
        define the evaluation set to get empirical coverage.
    """
    levels = _check_levels(quantile_levels)
    lower_level = (1.0 - nominal) / 2.0
    upper_level = 1.0 - lower_level

    matches = np.flatnonzero(np.isclose(levels, lower_level))
    if matches.size == 0:
        raise ValueError(
            f"no quantile level matches {lower_level} "
            f"(needed for {nominal:.0%} coverage)"
        )
    lower_index = int(matches[0])
    upper_index = int(np.flatnonzero(np.isclose(levels, upper_level))[0])

    observations = np.asarray(observations, dtype=np.float64)
    forecasts = np.asarray(forecasts, dtype=np.float64)
    return (observations >= forecasts[..., lower_index]) & (
        observations <= forecasts[..., upper_index]
    )


def median_absolute_error(
    observations: np.ndarray,
    forecasts: np.ndarray,
    quantile_levels: Sequence[float] = DEMO_QUANTILE_LEVELS,
) -> np.ndarray:
    """Absolute error of the predictive median, in the units of the data."""
    levels = _check_levels(quantile_levels)
    median_index = int(np.flatnonzero(np.isclose(levels, 0.5))[0])
    return np.abs(
        np.asarray(observations, dtype=np.float64)
        - np.asarray(forecasts, dtype=np.float64)[..., median_index]
    )
