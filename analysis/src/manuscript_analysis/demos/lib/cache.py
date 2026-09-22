"""Versioned caching of derived arrays, on top of epymorph's cache.

This deliberately does **not** introduce a second cache. epymorph already
provides a versioned bundle cache (`epymorph.cache.save_bundle_to_cache` /
`load_bundle_from_cache`), which is the same mechanism the built-in ADRIOs use
for their own derived files. Building on it means:

- one cache location, controllable via the `EPYMORPH_CACHE_PATH` environment
  variable, which is what a container should set;
- one eviction path, the `epymorph cache` command line tooling;
- no project-local `cache/` directory to gitignore or ship.

Use this for slow *derived* results (fit outputs, projected matrices). Raw
source files fetched from a URL should use `epymorph.cache.load_or_fetch_url`
directly, as `demolib/contacts.py` does.
"""

from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import numpy as np
from epymorph.cache import (
    CacheMissError,
    FileError,
    load_bundle_from_cache,
    save_bundle_to_cache,
)

CACHE_ROOT = Path("demolib")


def cached_arrays(
    name: str,
    version: int,
    compute: Callable[[], dict[str, np.ndarray]],
) -> dict[str, np.ndarray]:
    """Return the arrays from `compute()`, loading from the cache if available.

    Invalidation is by version stamp only. Bump `version` when the *meaning* of
    the cached arrays changes; the cache does not inspect their contents.

    Parameters
    ----------
    name :
        Cache key, unique within this project.
    version :
        Version stamp. A cached bundle older than this is ignored and recomputed.
    compute :
        Called only on a cache miss. Must return a dict of named arrays.

    Returns
    -------
    :
        The arrays, either loaded from the cache or freshly computed.
    """
    path = CACHE_ROOT / f"{name}.tgz"

    try:
        bundle = load_bundle_from_cache(path, version_at_least=version)
        return {
            key.removesuffix(".npy"): np.load(value, allow_pickle=False)
            for key, value in bundle.items()
        }
    except (CacheMissError, FileError):
        # A miss, or a bundle written by an older version. Recompute either way.
        pass

    arrays = compute()

    files = {}
    for key, array in arrays.items():
        buffer = BytesIO()
        np.save(buffer, array, allow_pickle=False)
        buffer.seek(0)
        files[f"{key}.npy"] = buffer
    save_bundle_to_cache(path, version, files)

    return arrays
