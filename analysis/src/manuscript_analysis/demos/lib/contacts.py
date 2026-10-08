"""Age-mixing contact matrices for the influenza demo.

Source data is Mistry et al. (2021), *Inferring high-resolution human mixing
patterns for disease modeling*, Nature Communications 12:323, distributed under
Apache-2.0 at https://github.com/mobs-lab/mixing-patterns.

Files are fetched on demand and cached using epymorph's own cache, the same
mechanism the built-in ADRIOs use, so nothing is committed to this repository
and the cache is managed by the usual epymorph tooling. The URLs are pinned to a
commit rather than a branch, so a given release of this code always reads the
same bytes.

Method reference: `demo-flu/contact-matrix-methods.md`.

Structure
---------
This module is deliberately shaped like an `epymorph.adrio.adrio.FetchADRIO`, so
that moving it upstream is a lift rather than a rewrite. That class splits into:

- `_fetch(context)`, which talks to the network and the cache. Here that is
  `fetch_source` and `fetch_state_sources`.
- `_process(context, data)`, a pure transform with no I/O. Here that is
  `aggregate`, `project`, `normalize`, and `contact_matrix`, which together take
  the source data plus the target demography and return an `(N, A, A)` array.

The blocker for actually being an ADRIO is that epymorph has no `(N, A, A)` data
shape, so an ADRIO cannot declare this result format. Everything in `_process`
already produces that array; only the plumbing in `demolib/params/contact_wiring.py`
is a workaround, and it disappears when the shape exists.

Public API
----------
Seven names carry the models. A reader following `demo-flu/models/` needs only these:

- `FLU_STRATA`, `AgeBand` -- the six age bands the demo uses.
- `SourceContacts` -- one location's matrix and the demography it was measured on.
- `fetch_source`, `fetch_state_sources` -- national and per-state source matrices.
- `aggregate` -- collapse the source's 85 single-year bands onto the model's strata.
- `contact_matrix` -- the whole pipeline: project, select a mixing structure,
  normalize to unit spectral radius. This is the only entry point the RUMEs use.

The rest are internal steps of `contact_matrix`: `project`, `normalize`,
`homogeneous_matrix` and `spectral_radius`.

Trimmed 2026-09-15 when `demo-flu/contact-matrices.ipynb` was superseded. The
contact-balance validators moved to `scratch/smoke_contacts.py`, which is where they
are actually exercised; `load_setting_mixture` and `prefetch` were removed outright.
Recover any of them from git history or the superseded notebook if needed.
"""

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import NamedTuple

import numpy as np
from epymorph.cache import load_or_fetch_url

from manuscript_analysis.demos import paths

# Grouped by purpose rather than sorted: the point is to show a reader which
# seven names carry the models.
__all__ = [  # noqa: RUF022
    # The model path.
    "AgeBand",
    "FLU_STRATA",
    "SourceContacts",
    "aggregate",
    "contact_matrix",
    "fetch_source",
    "fetch_state_sources",
    # Internal steps of `contact_matrix`, exported for inspection.
    "MIXING_OPTIONS",
    "homogeneous_matrix",
    "normalize",
    "project",
    "spectral_radius",
]

# NOTE: epymorph's `module_cache_path(__name__)` cannot be used here. It walks
# parent directories looking for one named "epymorph" and never terminates for a
# module outside that package, because `Path("/").parent == Path("/")`. Any
# third-party ADRIO author hits this immediately. Reported 2026-08-28; see
# `project-notes/handoff.md`. The path is relative to epymorph's cache root,
# which is what `load_or_fetch_url` expects, so we still share the epymorph cache.
CACHE_PATH = Path("demolib") / "contacts"

# Pinned to a commit, not a branch: the URL must always return the same bytes.
# This is the repository HEAD as of 2026-08-28; it has not changed since 2021.
MISTRY_COMMIT = "1a28882617cab97a9578c2af8fd21d9e582e12a2"
MISTRY_BASE_URL = (
    f"https://raw.githubusercontent.com/mobs-lab/mixing-patterns/{MISTRY_COMMIT}/data"
)

# Contact weights used by Mistry et al. to combine the per-setting matrices into
# the overall matrix. Retained so a setting-specific
# counterfactual (for example, school closure) is possible without re-deriving them.
SETTING_WEIGHTS = {
    "household": 4.11,
    "school": 11.41,
    "work": 8.07,
    "community": 2.79,
}

# The oldest band in the source data is "84 and over".
MAX_AGE = 84


class AgeBand(NamedTuple):
    """One model stratum, as an inclusive range of single years of age."""

    name: str
    lower: int
    upper: int


# The six ACS bands used by Demo 1. Mistry's single-year resolution reproduces
# these boundaries exactly, which is why it is preferred over Prem et al.
FLU_STRATA = (
    AgeBand("age_00-04", 0, 4),
    AgeBand("age_05-17", 5, 17),
    AgeBand("age_18-49", 18, 49),
    AgeBand("age_50-64", 50, 64),
    AgeBand("age_65-74", 65, 74),
    AgeBand("age_75-99", 75, MAX_AGE),
)


class SourceContacts(NamedTuple):
    """A contact matrix together with the demography it was measured in.

    A contact matrix is only meaningful alongside its own population, because
    reciprocity (`C_ij * N_i == C_ji * N_j`) is defined relative to it. Keeping
    the two together makes it hard to project one without the other.
    """

    matrix: np.ndarray
    """Contacts per day; `matrix[i, j]` is contacts of one person in `i` with people in `j`."""

    population: np.ndarray
    """Population per band, in the same order as `matrix`."""

    bands: tuple[AgeBand, ...] | None
    """The strata, once aggregated. `None` while still at single-year resolution."""


MISTRY_DIR = paths.RAW / "mistry"
"""The Mistry files the models read, frozen with their provenance. `CACHE_PATH`, in
epymorph's own cache, is only where a first download lands on its way here."""


def _fetch(path: str) -> BytesIO:
    """A file from the pinned Mistry release, read from `data/raw/` once it is frozen there.

    The first call downloads it and freezes it beside a provenance record; every later call,
    on any machine, reads the file and checks it against that record.
    """
    url = f"{MISTRY_BASE_URL}/{path}"
    local = MISTRY_DIR / path.replace("/", "_")
    record = local.with_suffix(".provenance.json")
    if not local.exists():
        data = load_or_fetch_url(url, CACHE_PATH / path.replace("/", "_")).getvalue()
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(data)
        record.write_text(json.dumps({
            "url": url,
            "sha256": sha256(data).hexdigest(),
            "frozen_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "license": "Apache-2.0 (https://github.com/mobs-lab/mixing-patterns)",
        }, indent=2) + "\n")
    data = local.read_bytes()
    if json.loads(record.read_text())["sha256"] != sha256(data).hexdigest():
        raise ValueError(f"{local} no longer matches {record.name}")
    return BytesIO(data)


def _location_stem(location: str) -> str:
    """Build the filename stem for a location.

    ``"United_States"`` selects the national matrix; any other value is treated
    as a US state or territory name with underscores, e.g. ``"New_York"``.
    """
    if location == "United_States":
        return "United_States_country_level"
    return f"United_States_subnational_{location}"


# Mistry's subnational filenames use the full state name with underscores. The
# scope's labels are USPS codes, so a lookup is needed to go from one to the
# other. Puerto Rico and the other territories are absent from the dataset.
STATE_LOCATIONS = {
    "AK": "Alaska", "AL": "Alabama", "AR": "Arkansas", "AZ": "Arizona",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DC": "District_of_Columbia", "DE": "Delaware", "FL": "Florida",
    "GA": "Georgia", "HI": "Hawaii", "IA": "Iowa", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "MA": "Massachusetts", "MD": "Maryland", "ME": "Maine",
    "MI": "Michigan", "MN": "Minnesota", "MO": "Missouri", "MS": "Mississippi",
    "MT": "Montana", "NC": "North_Carolina", "ND": "North_Dakota",
    "NE": "Nebraska", "NH": "New_Hampshire", "NJ": "New_Jersey",
    "NM": "New_Mexico", "NV": "Nevada", "NY": "New_York", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode_Island", "SC": "South_Carolina", "SD": "South_Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VA": "Virginia",
    "VT": "Vermont", "WA": "Washington", "WI": "Wisconsin",
    "WV": "West_Virginia", "WY": "Wyoming",
}
"""USPS code to Mistry subnational location name, for all 50 states and DC."""


def fetch_source(
    location: str = "United_States", setting: str = "overall"
) -> SourceContacts:
    """Load a Mistry contact matrix and its age distribution.

    Parameters
    ----------
    location :
        ``"United_States"`` for the national matrix, or a state name with spaces
        replaced by underscores, e.g. ``"Arizona"``, ``"New_York"``.
    setting :
        ``"overall"`` for the combined matrix, or one of ``"household"``,
        ``"school"``, ``"work"``, ``"community"``. **The per-setting matrices use
        a different normalization** and must be scaled by `SETTING_WEIGHTS`
        before they are comparable to the overall matrix.

    Returns
    -------
    :
        The single-year-resolution matrix and the population it belongs to.
    """
    stem = _location_stem(location)

    if setting == "overall":
        matrix_path = f"contact_matrices/{stem}_M_overall_contact_matrix_85.csv"
    elif setting in SETTING_WEIGHTS:
        matrix_path = f"contact_matrices/{stem}_F_{setting}_setting_85.csv"
    else:
        options = ["overall", *SETTING_WEIGHTS]
        raise ValueError(f"unknown setting {setting!r}; expected one of {options}")

    matrix = np.loadtxt(_fetch(matrix_path), delimiter=",")
    population = np.loadtxt(
        _fetch(f"age_distributions/{stem}_age_distribution_85.csv"), delimiter=","
    )[:, 1]

    expected = MAX_AGE + 1
    if matrix.shape != (expected, expected):
        raise ValueError(
            f"expected a ({expected}, {expected}) matrix, got {matrix.shape}"
        )
    if population.shape != (expected,):
        raise ValueError(f"expected a ({expected},) population, got {population.shape}")

    return SourceContacts(matrix=matrix, population=population, bands=None)


def fetch_state_sources(
    labels: Sequence[str],
    bands: Sequence[AgeBand] = FLU_STRATA,
) -> list[SourceContacts]:
    """One aggregated Mistry source matrix per state, in the scope's node order.

    Each state gets its **own** measured matrix, rather than the national one.
    The result is ordered to match `labels`, so it can be indexed by node.

    Parameters
    ----------
    labels :
        USPS state codes in the scope's node order, i.e. `scope.labels`.
    bands :
        The strata to aggregate to; must match the RUME's strata.

    Returns
    -------
    :
        One aggregated source per label, same order.
    """
    unknown = [label for label in labels if label not in STATE_LOCATIONS]
    if unknown:
        raise ValueError(f"no Mistry subnational matrix for: {sorted(unknown)}")
    return [
        aggregate(fetch_source(STATE_LOCATIONS[label]), bands) for label in labels
    ]


def aggregate(
    source: SourceContacts,
    bands: tuple[AgeBand, ...] = FLU_STRATA,
) -> SourceContacts:
    """Aggregate a single-year matrix to coarser strata.

    The two matrix indices are aggregated differently, and they are not
    interchangeable:

    - Over the **contactee** (column) index, contacts are **summed**. Contacts
      with 5-9-year-olds and with 10-14-year-olds add up.
    - Over the **contactor** (row) index, contacts are **averaged, weighted by
      population**. An average member of the 5-17 stratum is a population
      weighted mixture of the single years it contains.

    This is the standard "averaged row, summed column" convention. It follows
    from the definition of the matrix: per-capita on the contactor side, total on
    the contactee side.

    Aggregation preserves contact balance, so `contact_balance_error` should be unchanged
    by this step. See the lemma in `demo-flu/contact-matrix-methods.md` §3.
    """
    if source.bands is not None:
        raise ValueError("this matrix has already been aggregated")

    indices = [np.arange(band.lower, band.upper + 1) for band in bands]

    populations = np.array([source.population[i].sum() for i in indices])
    if np.any(populations <= 0):
        raise ValueError("every band must contain a positive population")

    matrix = np.zeros((len(bands), len(bands)), dtype=np.float64)
    for i, rows in enumerate(indices):
        weights = source.population[rows] / source.population[rows].sum()
        for j, columns in enumerate(indices):
            # Sum over the contactee band, then population-weight over the
            # contactor band.
            contacts_with_band_j = source.matrix[np.ix_(rows, columns)].sum(axis=1)
            matrix[i, j] = weights @ contacts_with_band_j

    return SourceContacts(matrix=matrix, population=populations, bands=bands)


def spectral_radius(matrix: np.ndarray) -> float:
    """Largest absolute eigenvalue.

    This is the factor that sets `R0`: under the force of infection used here,
    `R0 = (q / gamma) * spectral_radius(C)`. Dividing the matrix by it therefore
    makes the single fitted parameter `q` mean exactly `R0 * gamma`, in every node
    and every model.
    """
    return float(np.max(np.abs(np.linalg.eigvals(matrix))))


# --- The `_process` half: pure transforms, no I/O ------------------------------


def project(
    source: SourceContacts,
    target_populations: np.ndarray,
) -> np.ndarray:
    """Project a contact matrix onto a different demography.

    Implements **Method 2 (density correction)** of Arregui S, Aleta A, Sanz J,
    Moreno Y, *Projecting social contact matrices to different demographic
    structures*, PLoS Comput Biol 2018;14(12):e1006638, their Eq 5:

        C'_ij = C_ij * (N * N'_j) / (N_j * N')

    The matrix is read as an **intrinsic connectivity** (who a person prefers to
    contact, by age) multiplied by the **density of available contactees**
    (`N_j / N`). Projecting means keeping the preferences and substituting the
    target densities. Arregui et al. find the intrinsic part to be the
    transferable one, and prefer this to their Method 1, which merely averages
    away the reciprocity discrepancy.

    Their Method 3 adds a rescaling to preserve mean connectivity. It is
    equivalent to Method 2 here: it differs only by an overall scalar, which the
    freely estimated transmission parameter absorbs. That is their scenario 1.

    Parameters
    ----------
    source :
        An aggregated matrix and the demography it belongs to.
    target_populations :
        Shape `(N, A)`: population per node per stratum, in the same stratum
        order as `source`. This is the model's own demography, from ACS.

    Returns
    -------
    :
        Shape `(N, A, A)`: one projected matrix per node.

    Notes
    -----
    Reciprocity is *preserved*, not *created*. If `source` is not reciprocal in
    its own demography, the output will not be reciprocal either. Check the
    source with `contact_balance_error` first.
    """
    if source.bands is None:
        raise ValueError("project expects an aggregated matrix; call aggregate first")

    target = np.asarray(target_populations, dtype=np.float64)
    if target.ndim != 2 or target.shape[1] != len(source.bands):
        raise ValueError(
            f"target_populations must be (N, {len(source.bands)}), got {target.shape}"
        )
    if np.any(target <= 0):
        raise ValueError("every node and stratum must have a positive population")

    source_total = source.population.sum()
    target_total = target.sum(axis=1)

    # C'[n, i, j] = C[i, j] * (N * N'[n, j]) / (N[j] * N'[n])
    density_ratio = (source_total * target) / (
        source.population[None, :] * target_total[:, None]
    )
    return source.matrix[None, :, :] * density_ratio[:, None, :]


def normalize(matrices: np.ndarray) -> np.ndarray:
    """Scale each node's matrix to unit spectral radius.

    After this, the transmission scalar `q` means `R0 * gamma` in every node and
    in every arm, because `R0 = (q / gamma) * rho(C)` under the force of
    infection used here.

    This is the standard next-generation-matrix scaling (Diekmann, Heesterbeek
    and Roberts 2010). It cannot change the fit, only the interpretation of `q`,
    because `q` is freely estimated and absorbs any constant factor.
    """
    if matrices.ndim != 3:
        raise ValueError(f"expected (N, A, A), got {matrices.shape}")
    radii = np.array([spectral_radius(m) for m in matrices])
    if np.any(radii <= 0):
        raise ValueError("every node's matrix must have a positive spectral radius")
    return matrices / radii[:, None, None]


MIXING_OPTIONS = ("empirical", "homogeneous", "within_group")
"""The mixing structures `contact_matrix` can build. See its docstring."""


def homogeneous_matrix(target_populations: np.ndarray) -> np.ndarray:
    """Mixing with no age preference: contact in proportion to group size.

    `C_ij = N_j / N`. Every row is identical, so a person of any age spends the
    same fraction of their contact on group `j`, namely that group's share of the
    population. This is what a model assumes when no contact matrix is available,
    and it is the natural comparison for asking whether a measured matrix helps.

    The result needs no normalization: every row sums to 1 and the matrix is
    rank 1, so its spectral radius is exactly 1 already.

    Returns
    -------
    :
        Shape `(N, A, A)`.
    """
    target = np.asarray(target_populations, dtype=np.float64)
    if target.ndim != 2:
        raise ValueError(f"target_populations must be (N, A), got {target.shape}")
    shares = target / target.sum(axis=1, keepdims=True)
    # Broadcast each node's share vector across all rows.
    return np.repeat(shares[:, None, :], target.shape[1], axis=1)


def contact_matrix(
    source: SourceContacts,
    target_populations: np.ndarray,
    mixing: str = "empirical",
) -> np.ndarray:
    """Build the per-node contact matrix for one model configuration.

    Parameters
    ----------
    mixing :
        Which mixing structure to build.

        - ``"empirical"``: the measured matrix, projected onto the target
          demography. Age groups mix at the rates people actually report.
        - ``"homogeneous"``: no age preference; contact in proportion to group
          size (`C_ij = N_j / N`). What you assume when you have no matrix.
          Ignores `source` apart from its stratum count.
        - ``"within_group"``: the empirical within-group rates with all
          between-group contact removed (implemented by zeroing the off-diagonal
          entries). Note this leaves the groups fully decoupled and their relative
          transmissibilities untouched, so most of them fall below the epidemic
          threshold. See `contact-matrix-methods.md` §7.

    Returns
    -------
    :
        Shape `(N, A, A)`, each node's matrix normalized to unit spectral radius,
        so the fitted `q` means `R0 * gamma` identically across configurations.

    Notes
    -----
    The configurations differ **only** through this argument. The `meta_edges`
    code is identical, which makes the comparison a change of data rather than of
    code.

    Because every configuration is normalized, none of them can differ in the
    leading *eigenvalue* of their mixing matrix, only in its leading
    *eigenvector*. The comparison therefore tests the shape of mixing, holding
    overall transmissibility free.
    """
    if mixing == "homogeneous":
        return normalize(homogeneous_matrix(target_populations))

    projected = project(source, target_populations)

    if mixing == "empirical":
        selected = projected
    elif mixing == "within_group":
        selected = np.zeros_like(projected)
        diagonal = np.arange(projected.shape[1])
        selected[:, diagonal, diagonal] = projected[:, diagonal, diagonal]
    else:
        raise ValueError(f"unknown mixing {mixing!r}; expected one of {MIXING_OPTIONS}")

    return normalize(selected)
