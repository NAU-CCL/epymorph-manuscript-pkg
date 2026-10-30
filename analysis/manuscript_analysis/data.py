"""An ADRIO wrapper that persists values and their acquisition provenance.

Copied from Tyler Coles's `reproducible-manuscript-poc` (`analysis/fair_epymorph_poc/data.py`,
commit ef4fd7a, 2026-09-28), unchanged apart from this docstring and two changes, each
marked CHANGED: a condition in `inspect`, so that it can cache an ADRIO whose result has an
open-ended axis; and the wrapped ADRIO's requirements passed through, so that it can cache
an ADRIO that takes another as input (`PopulationByAge` takes the age table).
It is headed for epymorph itself; once it is released there, import it from epymorph and
delete this file.

The copied code is under the MIT License:

    Copyright (c) 2026 Reproducible Epymorph Manuscript POC contributors

    Permission is hereby granted, free of charge, to any person obtaining a copy of this
    software and associated documentation files (the "Software"), to deal in the Software
    without restriction, including without limitation the rights to use, copy, modify,
    merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
    permit persons to whom the Software is furnished to do so, subject to the following
    conditions:

    The above copyright notice and this permission notice shall be included in all copies
    or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
    INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
    PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
    CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR
    THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, cast, override

import numpy as np
from epymorph.adrio.adrio import (
    ADRIO,
    ADRIOProcessingError,
    InspectResult,
)
from epymorph.adrio.validation import ResultFormat
from epymorph.simulation import Context
from numpy.typing import NDArray

__all__ = [
    "ProvenanceCachedADRIO",
    "ProvenanceCacheError",
    "CACHE_SCHEMA_VERSION",
]

CACHE_SCHEMA_VERSION = 1


class ProvenanceCacheError(RuntimeError):
    """The cache is absent, corrupt, or mismatches its provenance."""


def array_sha256(values: NDArray[Any]) -> str:
    normalized = np.ascontiguousarray(values)
    return sha256(normalized.tobytes()).hexdigest()


def provenance_path(cache_path: Path) -> Path:
    return cache_path.with_suffix(".provenance.json")


def read_provenance(
    provenance_path: Path,
    description: str,
    values: NDArray[Any],
) -> dict[str, object]:
    try:
        raw_provenance: object = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProvenanceCacheError(
            f"Invalid provenance file: {provenance_path}"
        ) from error
    if not isinstance(raw_provenance, dict):
        raise ProvenanceCacheError(f"Invalid provenance record: {provenance_path}")

    provenance = cast(dict[str, object], raw_provenance)
    if provenance.get("schema_version") != CACHE_SCHEMA_VERSION:
        raise ProvenanceCacheError("Unsupported cache schema version.")
    if provenance.get("description") != description:
        raise ProvenanceCacheError("Cache provenance does not match this ADRIO.")
    if provenance.get("values_sha256") != array_sha256(values):
        raise ProvenanceCacheError("Cache content does not match its provenance.")
    return provenance


def write_provenance(
    provenance_path: Path,
    description: str,
    values: NDArray[Any],
) -> None:
    provenance: dict[str, object] = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "description": description,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "values_sha256": array_sha256(values),
    }
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class ProvenanceCachedADRIO[ResultT: np.generic, ValueT: np.generic](
    ADRIO[ResultT, ValueT]
):
    """Cache an ADRIO's result array with a provenance record."""

    _wrapped: ADRIO[ResultT, ValueT]
    _cache_path: Path
    _description: str

    def __init__(
        self,
        wrapped: ADRIO[ResultT, ValueT],
        cache_path: Path,
        description: str,
    ) -> None:
        self._wrapped = wrapped
        self._cache_path = Path(cache_path)
        self._description = description
        # CHANGED from the original, which declared no requirements, so an ADRIO that
        # needs another attribute (PopulationByAge needs population_by_age_table) never
        # received it on a cache miss. A cached result is read without them either way.
        self.requirements = wrapped.requirements

    @property
    def result_format(self) -> ResultFormat:
        return self._wrapped.result_format

    @override
    def validate_context(self, context: Context) -> None:
        self._wrapped.validate_context(context)

    @override
    def inspect(self) -> InspectResult[ResultT, ValueT]:
        # If both cache and provenance are absent, this is a normal cache miss.
        # If either exists without the other, or they're not files, that's an error.
        cache_path = self._cache_path
        prov_path = provenance_path(cache_path)
        cache_hit = cache_path.exists() and prov_path.exists()

        result = (
            self._load_cached(cache_path, prov_path)
            if cache_hit
            else self._load_deferred()
        )

        # CHANGED from the original, which validated unconditionally. This generic check
        # cannot handle a result with an open-ended axis (ACS's age table is N x A), and the
        # wrapped ADRIO's own check needs the Census API, which is what the cache avoids. A
        # fetched result has passed the wrapped ADRIO's own validation already, and a cached
        # one is held to its provenance checksum.
        if -1 not in self.result_format.shape.to_tuple(self.context.dim):
            self.validate_result(self.context, result.result)

        if not cache_hit:
            # If cache missed and result is valid, write cache and provenance.
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            values = np.asarray(result.result)
            np.savez_compressed(cache_path, result=values)
            write_provenance(prov_path, self._description, values)

        return result

    def _load_cached(
        self, cache_path: Path, prov_path: Path
    ) -> InspectResult[ResultT, ValueT]:
        # Cache hit! Read the cached values and validate the provenance.
        if not cache_path.is_file() or not prov_path.is_file():
            err = f"Expected cache and provenance at {cache_path} and {prov_path}."
            raise ProvenanceCacheError(err)
        try:
            with np.load(cache_path, allow_pickle=False) as archive:
                values = cast(NDArray[ResultT], np.asarray(archive["result"]))
        except (OSError, KeyError, ValueError) as error:
            err = f"Unable to load ADRIO cache: {cache_path}"
            raise ProvenanceCacheError(err) from error

        read_provenance(prov_path, self._description, values)
        return InspectResult(
            adrio=self,
            source=None,
            result=values,
            dtype=self.result_format.dtype.type,  # type: ignore[reportUnknownMemberType]
            shape=self.result_format.shape,
            issues={},
        )

    def _load_deferred(self) -> InspectResult[ResultT, ValueT]:
        # Cache miss! Defer to the wrapped ADRIO.
        self.validate_context(self.context)
        result = self.defer_context(self._wrapped).inspect()
        if result.issues:
            issue_names = ", ".join(result.issues)
            raise ADRIOProcessingError(
                self,
                self.context,
                f"ADRIO data contains unresolved issues: {issue_names}.",
            )
        return dataclasses.replace(result, adrio=self)
