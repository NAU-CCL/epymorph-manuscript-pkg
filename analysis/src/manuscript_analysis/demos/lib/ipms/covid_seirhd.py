"""SEIRHD for the COVID demo.

An exposed compartment and a hospital compartment, with deaths arriving **only** via
hospitalization, so `E + I + H` set the lag between infection and death. That routing is
what lets one likelihood fit two observed quantities at once: the hospital census is the
`H` compartment, a stock, and deaths are the `H -> D` event, a flow.

Not in `epymorph.data.ipm`, which is why it lives here. See
`demo-covid/refactor-plan-v01.md`.
"""

from epymorph.attribute import AttributeDef
from epymorph.compartment_model import (
    CompartmentModel,
    compartment,
    edge,
    fork,
)
from epymorph.data_shape import Shapes
from sympy import Max

__all__ = ["CENSUS_COMPARTMENT", "DEATHS_EVENT", "SEIRHD"]

CENSUS_COMPARTMENT = "H"
"""The compartment the hospital census observes: a stock."""

DEATHS_EVENT = "H → D"
"""The event the death counts observe: a flow."""


class SEIRHD(CompartmentModel):
    """SEIRHD. Deaths arrive only via hospitalization, so E + I + H set the death lag."""

    compartments = (
        compartment("S"),
        compartment("E"),
        compartment("I"),
        compartment("R"),
        # Neither the hospitalized nor the dead commute.
        compartment("H", tags=["immobile"]),
        compartment("D", tags=["immobile"]),
    )

    requirements = (
        AttributeDef("beta", type=float, shape=Shapes.TxN, comment="infectivity"),
        AttributeDef("sigma", type=float, shape=Shapes.TxN,
                     comment="rate of leaving the latent period"),
        AttributeDef("gamma", type=float, shape=Shapes.TxN,
                     comment="rate of leaving the infectious period"),
        AttributeDef("xi", type=float, shape=Shapes.TxN, comment="immune waning rate"),
        AttributeDef("hospitalization_prob", type=float, shape=Shapes.TxN,
                     comment="probability of hospitalization given infection"),
        AttributeDef("hospitalization_duration", type=float, shape=Shapes.TxN,
                     comment="mean duration of hospitalization, in days"),
        AttributeDef("death_prob", type=float, shape=Shapes.TxN,
                     comment="deaths per hospitalization-equivalent"),
    )

    def edges(self, symbols):
        [S, E, I, R, H, D] = symbols.all_compartments
        [beta, sigma, gamma, xi, h_prob, h_dur, d_prob] = symbols.all_requirements

        # The dead leave the mixing population; the hospitalized do not.
        N_alive = Max(1, S + E + I + R + H)

        return [
            edge(S, E, rate=beta * S * I / N_alive),
            edge(E, I, rate=sigma * E),
            fork(
                edge(I, H, rate=gamma * I * h_prob),
                edge(I, R, rate=gamma * I * (1 - h_prob)),
            ),
            fork(
                edge(H, D, rate=H / h_dur * d_prob),
                edge(H, R, rate=H / h_dur * (1 - d_prob)),
            ),
            edge(R, S, rate=xi * R),
        ]
