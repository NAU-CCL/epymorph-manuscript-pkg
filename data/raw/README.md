# data/raw

Raw, unmodified inputs the demo models read, each frozen beside a provenance record. With
these in place a build needs no Census API key and downloads nothing from the Census API or
GitHub. Never hand-edit files in this directory.

| files | what | from |
|---|---|---|
| `covid-population-counties-2015-ma-ct-nh.npz` | population of the 32 counties | ACS 5-year, via epymorph's `acs5.Population` |
| `covid-population-states-2015-ma-ct-nh.npz` | population of the 3 states | the same |
| `covid-commuters-counties-2015-ma-ct-nh.npz` | commuting flows between the counties | ACS commuting flows, via `commuting_flows.Commuters` |
| `flu-population-by-age-2024-52-states.npz` | population by age (table B01001) for all 52 jurisdictions | ACS 5-year, via `acs5.PopulationByAgeTable` |
| `flu-population-<ages>-2024-52-states.npz` | each of the six age groups' population, summed from that table | `acs5.PopulationByAge`, frozen 2026-10-08: it checks for a Census key even when handed the table |
| `mistry/` | the US contact matrix by single year of age, and its age distribution | Mistry et al. 2021, `mobs-lab/mixing-patterns` at a pinned commit, Apache-2.0 |

**How they got here.** Each is fetched the first time the code needs it and frozen with a
`.provenance.json` beside it (what it is, when it was frozen, and a SHA-256 of its values or
bytes); every later read, on any machine, loads the file and checks it against that record.
The Census inputs go through `ProvenanceCachedADRIO` (`analysis/src/manuscript_analysis/data.py`,
from Tyler Coles's reproducible-manuscript skeleton). File names carry the season's ACS
vintage and states, so a changed season fetches its own files rather than reading stale
ones. The Mistry files were frozen by the pre-restructure code; `flu_inputs.py` only reads
them, checking each against its record, and the record holds the pinned URL to download
it from again.

**To refresh one deliberately**, delete the file and its provenance record and run the
notebook that needs it with a Census API key in the environment, for example
`set -a; . ./.env; set +a` from the repository root first (nothing loads `.env` by
itself). Expect numbers to move if the source has changed.

**What still needs the network, once per machine:** the geographic scopes. epymorph builds
a `StateScope` or `CountyScope` from Census TIGER summary files, which it downloads (no key
needed) and keeps in its own cache. TIGER vintages are published once and not revised.

The lit-search evidence does not live here. It is nested by topic instead, so that its three
layers sit together:

    data/lit-search/raw/        the archived PubMed and Lens.org exports
    data/lit-search/decisions/  the hand-entered screening and mark decisions
    results/lit-search/         everything the pipeline generates from the two

Those exports cannot be re-fetched: the same Lens query that returned 1,009 records in July
2026 returns more every month, so they are the only copy of what Appendix S1's numbers were
computed from. `results/lit-search/MANIFEST.sha256` checksums them, and the pipeline fails if
any of them changes.
