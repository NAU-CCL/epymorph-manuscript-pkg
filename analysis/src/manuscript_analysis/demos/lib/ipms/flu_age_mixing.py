"""Age-structured mixing for the flu demo.

Builds a `MultiStrataRUMEBuilder` whose meta edges carry **all** transmission, so the
only thing that distinguishes one mixing structure from another is the contact matrix
supplied in `params`. See `demo-flu/contact-matrix-methods.md`.

Force of infection on stratum `i`, per node::

    rate(S_i -> I_i) = S_i * q * eta_i * sum_j C_ij * I_j / N_j

`q` is the shared transmissibility (with `C` normalized to unit spectral radius,
`q = R0 * gamma`); `eta_i` is a static per-recipient correction to row `i` of `C`.
"""

from collections.abc import Sequence

from epymorph.attribute import AttributeDef
from epymorph.compartment_model import (
    MultiStrataModelSymbols,
    TransitionDef,
    edge,
)
from epymorph.data_shape import Shapes
from epymorph.rume import GPM, MultiStrataRUMEBuilder
from sympy import Max

from manuscript_analysis.demos.lib.params.contact_wiring import contact_requirements

__all__ = ["age_mixing_rume_builder"]


def age_mixing_rume_builder(gpms: Sequence[GPM]) -> type[MultiStrataRUMEBuilder]:
    """A RUME builder class for `gpms`, one GPM per age stratum.

    The caller supplies the per-stratum IPM, MM and initializer, and must set
    `*::ipm::beta` to 0.0 in `params` so the base IPM does not double-count the
    transmission that `meta_edges` owns.

    Requires in `params`: `meta::ipm::q`, `meta::ipm::eta_0 .. eta_{A-1}`, and the
    `A * A` contact entries from `manuscript_analysis.demos.lib.params.contact_wiring.contact_params`.
    """
    gpms = list(gpms)
    names = [gpm.name for gpm in gpms]
    num_strata = len(names)
    if num_strata == 0:
        raise ValueError("at least one stratum is required")

    class AgeMixingRUME(MultiStrataRUMEBuilder):
        strata = tuple(gpms)

        # population_by_stratum is deliberately absent: IPM requirements resolve as
        # TxN and NxA does not broadcast to it. contact_wiring declares it instead.
        meta_requirements = (
            *contact_requirements(num_strata),
            # TxN, not N: q is supplied as a time-varying series once estimated.
            AttributeDef(name="q", type=float, shape=Shapes.TxN),
            *[
                AttributeDef(name=f"eta_{i}", type=float, shape=Shapes.TxN)
                for i in range(num_strata)
            ],
        )

        def meta_edges(
            self, symbols: MultiStrataModelSymbols
        ) -> list[TransitionDef]:
            compartments = [symbols.strata_compartments(n) for n in names]
            populations = [Max(1, sum(c)) for c in compartments]
            (q,) = symbols.requirements("q")

            edges = []
            for i in range(num_strata):
                S_i, I_i, _, _ = compartments[i]
                (eta_i,) = symbols.requirements(f"eta_{i}")
                rates = []
                for j in range(num_strata):  # unconditional: i == j lives here too
                    (c_ij,) = symbols.requirements(f"contact_{i}_{j}")
                    _, I_j, _, _ = compartments[j]
                    rates.append(q * eta_i * c_ij * S_i * I_j / populations[j])
                edges.append(edge(S_i, I_i, rate=sum(rates)))
            return edges

    return AgeMixingRUME
