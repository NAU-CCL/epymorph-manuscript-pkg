"""Wire a per-node contact matrix into a RUME.

**This module is a workaround, and should disappear.** epymorph has no `(N, A, A)`
data shape, so a contact matrix cannot be a single parameter. Until it can, each
entry `(i, j)` is declared separately as a scalar requirement of shape
`Shapes.N`, and supplied by one `ParamFunctionNode` per entry.

Everything epidemiological lives in `demolib/contacts.py`, which already returns
the `(N, A, A)` array. When the shape exists, that module becomes an ADRIO and
this one is deleted.

Why a `ParamFunction` rather than a precomputed array: the Arregui M2 projection
depends on the *target* demography, which epymorph itself supplies via ACS
ADRIOs. Deferring it to evaluation time means the projection follows the scope
instead of silently going stale when the scope, ACS year, or strata change.
"""

from collections.abc import Sequence

import numpy as np
from epymorph.attribute import AttributeDef
from epymorph.data_shape import Shapes
from epymorph.params import ParamFunctionNode

from manuscript_analysis.demos.lib.contacts import SourceContacts, contact_matrix


def population_by_stratum_attribute(
    name: str = "population_by_stratum",
) -> AttributeDef:
    """The target demography: population per node per stratum, shape `(N, A)`."""
    return AttributeDef(
        name=name,
        type=int,
        shape=Shapes.NxA,
        comment="population per node per stratum; the demography to project onto",
    )


def contact_attribute(i: int, j: int) -> AttributeDef:
    """Declare one contact-matrix entry as a per-node requirement."""
    return AttributeDef(
        name=f"contact_{i}_{j}",
        type=float,
        shape=Shapes.N,
        comment=f"normalized contacts/day, stratum {i} with stratum {j}",
    )


def contact_requirements(num_strata: int) -> list[AttributeDef]:
    """All `A * A` contact entries, for a RUME's `meta_requirements`."""
    return [
        contact_attribute(i, j) for i in range(num_strata) for j in range(num_strata)
    ]


class ContactMatrixEntry(ParamFunctionNode):
    """One entry of the projected, normalized contact matrix, per node.

    Reads the target demography from the simulation context and applies the full
    pipeline in `manuscript_analysis.demos.lib.contacts.contact_matrix`.

    Parameters
    ----------
    i, j :
        Which entry of the matrix this instance supplies.
    source :
        The aggregated source matrix and its own demography.
    mixing :
        Which mixing structure to build; see `manuscript_analysis.demos.lib.contacts.contact_matrix`.
        Every entry of a given configuration must be built with the same value.
    population_attribute :
        The attribute holding the target demography.
    """

    def __init__(
        self,
        i: int,
        j: int,
        source: SourceContacts | Sequence[SourceContacts],
        mixing: str = "empirical",
        population_attribute: AttributeDef | None = None,
    ):
        self.i = i
        self.j = j
        self.source = source
        self.mixing = mixing
        self._population = population_attribute or population_by_stratum_attribute()
        self.requirements = [self._population]

    def source_for(self, node_index: int) -> SourceContacts:
        """The source matrix this node is built from.

        One `SourceContacts` means every node shares an intrinsic connectivity
        and differs only through the M2 projection onto its own demography. A
        sequence means each node also brings its own measured matrix, and must
        be in the scope's node order.
        """
        if isinstance(self.source, SourceContacts):
            return self.source
        return self.source[node_index]

    def evaluate1(self, node_index: int) -> float:
        # `ParamFunctionNode.evaluate` is final, so this runs once per node per
        # entry. The projection is a 6x6 operation on one node, so recomputing it
        # is negligible next to the simulation itself; readability wins here.
        populations = self.data(self._population)
        node_populations = np.asarray(populations[node_index], dtype=np.float64)
        matrix = contact_matrix(
            self.source_for(node_index),
            node_populations[None, :],
            mixing=self.mixing,
        )
        return float(matrix[0, self.i, self.j])


def contact_params(
    source: SourceContacts | Sequence[SourceContacts],
    mixing: str = "empirical",
    prefix: str = "meta::ipm",
    population_attribute: AttributeDef | None = None,
) -> dict[str, ContactMatrixEntry]:
    """Build the `params` entries for every contact-matrix cell.

    Parameters
    ----------
    source :
        One aggregated source matrix shared by every node, or one per node in
        the scope's node order (see `manuscript_analysis.demos.lib.contacts.fetch_state_sources`).

    Returns
    -------
    :
        A mapping suitable for splatting into a RUME's `params`, e.g.
        ``{"meta::ipm::contact_0_0": ContactMatrixEntry(...), ...}``.
    """
    sources = [source] if isinstance(source, SourceContacts) else list(source)
    if not sources:
        raise ValueError("at least one source is required")
    if any(s.bands is None for s in sources):
        raise ValueError("every source must be aggregated to the model's strata first")
    strata_counts = {len(s.bands) for s in sources}  # type: ignore[arg-type]
    if len(strata_counts) > 1:
        raise ValueError(f"sources disagree on stratum count: {sorted(strata_counts)}")
    num_strata = strata_counts.pop()
    return {
        f"{prefix}::contact_{i}_{j}": ContactMatrixEntry(
            i, j, source, mixing=mixing, population_attribute=population_attribute
        )
        for i in range(num_strata)
        for j in range(num_strata)
    }
