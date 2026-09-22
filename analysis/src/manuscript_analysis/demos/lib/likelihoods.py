"""Observation likelihoods beyond the ones epymorph ships.

epymorph's `NegativeBinomialLikelihood` takes a single scalar `r`, which forces every
observed channel to share one dispersion. In an age-stratified fit the channels differ
by orders of magnitude in count and plausibly in reporting noise, so this adds a
per-channel version.

Like `demolib/params/contact_wiring.py`, this is a small epymorph extension that would be
reasonable to move upstream; it is kept here so the notebooks stay readable.
"""

from dataclasses import dataclass

import numpy as np
from epymorph.forecasting.likelihood import Likelihood
from numpy.typing import NDArray
from scipy.stats import nbinom
from typing_extensions import override

__all__ = ["PerChannelNegativeBinomial", "estimate_dispersion"]


@dataclass(frozen=True)
class PerChannelNegativeBinomial(Likelihood):
    """Negative binomial with one dispersion parameter per observed channel.

    The filter calls a likelihood per node with `observed` of shape `(Q,)` and
    `expected` of shape `(R, Q)`, so an `r` of shape `(Q,)` broadcasts along the
    last axis of both without any reshaping.

    Parameters
    ----------
    r :
        Dispersion per channel, shape `(Q,)`. All entries must be positive.
        **Higher r is tighter**: the variance is `mu + mu^2 / r`, so large r
        approaches Poisson and small r is heavily overdispersed.
    """

    r: NDArray[np.float64]

    def __post_init__(self):
        r = np.asarray(self.r, dtype=np.float64)
        if r.ndim != 1:
            raise ValueError(f"r must be one-dimensional, got shape {r.shape}")
        if not np.all(r > 0):
            raise ValueError("every dispersion parameter must be positive")
        object.__setattr__(self, "r", r)

    def _p(self, expected: NDArray[np.float64]) -> NDArray[np.float64]:
        return 1.0 / (1.0 + expected / self.r)

    @override
    def compute(self, observed, expected):
        return nbinom.pmf(observed, n=self.r, p=self._p(expected))

    @override
    def compute_log(self, observed, expected):
        return nbinom.logpmf(observed, n=self.r, p=self._p(expected))

    @override
    def sample(self, expected, rng):
        return np.array(nbinom.rvs(n=self.r, p=self._p(expected), random_state=rng))


def estimate_dispersion(
    observed: NDArray[np.float64],
    predicted: NDArray[np.float64],
    minimum: float = 1.0,
    maximum: float = 1000.0,
) -> NDArray[np.float64]:
    """Method-of-moments dispersion per channel, from residuals.

    For a negative binomial, `Var = mu + mu^2 / r`, so given the residual variance
    around the prediction, `r = mu^2 / (Var - mu)`.

    Parameters
    ----------
    observed, predicted :
        Matching arrays whose LAST axis is the channel. All other axes are pooled.
    minimum, maximum :
        Clamp. A channel whose residual variance is at or below its mean implies
        no overdispersion at all, which would send r to infinity or negative; those
        are clamped to `maximum`.

    Returns
    -------
    :
        Dispersion per channel, shape `(Q,)`.
    """
    observed = np.asarray(observed, dtype=np.float64)
    predicted = np.asarray(predicted, dtype=np.float64)
    if observed.shape != predicted.shape:
        raise ValueError(
            f"shapes must match, got {observed.shape} and {predicted.shape}"
        )

    channels = observed.shape[-1]
    flat_observed = observed.reshape(-1, channels)
    flat_predicted = predicted.reshape(-1, channels)

    mean = flat_predicted.mean(axis=0)
    variance = ((flat_observed - flat_predicted) ** 2).mean(axis=0)

    excess = variance - mean
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(excess > 0, mean**2 / excess, maximum)
    return np.clip(np.nan_to_num(r, nan=maximum, posinf=maximum), minimum, maximum)
