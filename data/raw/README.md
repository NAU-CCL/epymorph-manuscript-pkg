# data/raw

Raw, unmodified input data. Never hand-edit files in this directory: if a correction is
needed, regenerate from the original source and re-save here with that provenance documented.

The lit-search evidence does not live here. It is nested by topic instead, so that its three
layers sit together:

    data/lit-search/raw/        the archived PubMed and Lens.org exports
    data/lit-search/decisions/  the hand-entered screening and mark decisions
    results/lit-search/         everything the pipeline generates from the two

Those exports cannot be re-fetched: the same Lens query that returned 1,009 records in July
2026 returns more every month, so they are the only copy of what Appendix S1's numbers were
computed from. `results/lit-search/MANIFEST.sha256` checksums them, and the pipeline fails if
any of them changes.
