"""An Ornstein-Uhlenbeck process whose daily shocks are correlated across nodes.

epymorph's `OrnsteinUhlenbeck` draws an independent shock for every node every day. On
the county models that makes each county's parameter wander on its own, so within one
realization the 32 county forecasts are nearly independent, and summing them to a state
pulls the median up and narrows the spread. This class is the same process with one
change: the day's shocks are drawn jointly, `chol @ z`, where `chol` is the Cholesky
factor of a node-by-node correlation matrix.

Adapted from Jeff's `CorrelatedOU` in `FluSight-pipeline/flu/correlated.py`.

The correlation matrix must have ones on its diagonal. Then each node's own process,
and so its stationary distribution, is exactly the independent one; only how the nodes
move together changes.
"""

from typing import override

import numpy as np
from epymorph.data_shape import Shapes
from epymorph.forecasting.dynamic_params import ParamFunctionDynamics
from numpy.typing import NDArray


def spatial_correlation(
    distances: NDArray[np.float64], length_scale: float, shared: float
) -> NDArray[np.float64]:
    """`shared * exp(-d / length_scale) + (1 - shared) * I`.

    `shared` is the fraction of each node's shock that is spatially structured; the rest
    is the node's own. `shared=1` is a pure exponential kernel; `shared=0` is the
    independent process. Distances and length scale must be in the same units.
    """
    if not 0 <= shared <= 1:
        raise ValueError("shared must lie in [0, 1]")
    kernel = np.exp(-distances / length_scale)
    identity = np.eye(distances.shape[0])
    return shared * kernel + (1 - shared) * identity


class CorrelatedOU(ParamFunctionDynamics[np.float64]):
    """
    Model the time dependence of an unknown parameter as an Ornstein-Uhlenbeck process
    whose shocks are correlated across nodes. The process is parameterized in terms of
    each node's stationary distribution.

    Parameters
    ----------
    damping:
        The damping of the process. Must be positive.
    mean:
        The mean of the stationary distribution.
    standard_deviation:
        The standard deviation of the stationary distribution. Must be non-negative.
    chol:
        The lower-triangular Cholesky factor of the node-by-node correlation matrix.
    """

    damping: float | NDArray[np.float64]
    mean: float | NDArray[np.float64]
    standard_deviation: float | NDArray[np.float64]
    chol: NDArray[np.float64]

    requirements = ()

    def __init__(
        self,
        damping: float,
        mean: float,
        standard_deviation: float,
        chol: NDArray[np.float64],
    ):
        if np.any(damping <= 0):
            raise ValueError("Damping must be positive.")
        self.damping = damping
        self.mean = mean
        if np.any(standard_deviation < 0):
            raise ValueError("Standard deviation must be non-negative.")
        self.standard_deviation = standard_deviation
        if not np.allclose(np.sum(chol**2, axis=1), 1.0):
            raise ValueError("chol must factor a correlation matrix (unit diagonal).")
        self.chol = chol

    @override
    def _evaluate_from_initial(
        self, initial: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        if self.chol.shape != (self.scope.nodes, self.scope.nodes):
            raise ValueError(
                f"chol is {self.chol.shape}, the scope has {self.scope.nodes} nodes"
            )
        result = np.zeros((self.time_frame.days, self.scope.nodes), np.float64)
        previous = initial

        mean = Shapes.TxN.adapt(self.dim, np.array(self.mean))
        damping = Shapes.TxN.adapt(self.dim, np.array(self.damping))
        standard_deviation = Shapes.TxN.adapt(
            self.dim, np.array(self.standard_deviation)
        )
        delta_t = 1

        # The exact solution of the OU process over one day, as in epymorph's own.
        A = np.exp(-damping * delta_t)  # noqa: N806
        M = mean * (np.exp(-damping * delta_t) - 1)  # noqa: N806
        C = standard_deviation * np.sqrt(1 - np.exp(-2 * damping * delta_t))  # noqa: N806

        for i_day in range(self.time_frame.days):
            independent = self.rng.standard_normal(size=self.scope.nodes)
            shock = self.chol @ independent
            current = A[i_day, ...] * previous - M[i_day, ...] + C[i_day, ...] * shock
            result[i_day, ...] = current
            previous = current
        return result
