"""
Recall audit of the records the pre-filter set aside.

Three checks, matching the procedure reported in Appendix S1 §S1.1:

  1. Near-miss audit     — set-aside records carrying software + domain signal but no
                           inference term, the stratum most likely to hide a package that
                           describes its methods in non-standard vocabulary. Empty by
                           construction under the unified lexicon, which is the finding.
  2. Package-title sweep — every set-aside record whose TITLE carries a package-name cue
                           together with an epidemiology signal. Exhaustive, not sampled.
  3. Random-sample audit — a seeded random sample of the remaining set-aside records that
                           carry no package-title cue, bounding the miss rate there.

Run by `report.py`, after `screen.py` has written the set-aside records.
"""
import random
import re

from . import paths
from .lexicon import DOM, hits

SEED = 20260724
SAMPLE_N = 100

# A title-level cue that the record announces a named piece of software.
PKG_TITLE = [
    r"\b[A-Za-z][A-Za-z0-9]*\.(jl|py|R)\b",   # Pathogen.jl, foo.py
    r"\b[a-z]+[A-Z][A-Za-z0-9]*\b",           # camelCase: spatPomp, epiNow
    r"\b[A-Z][a-z]+[A-Z][A-Za-z0-9]*\b",      # CamelCase: SimInf, BayesianFitForecast
    r"\b[A-Z]{3,}\b",                         # ARBO, MEMILIO
    r"^[^:]{2,30}:",                          # "name: a package for ..."
    r"\b(package|toolbox|toolkit|library|software|framework)\b",
]


def title_cue(title):
    return any(re.search(pattern, title) for pattern in PKG_TITLE)


def main():
    rows = paths.read_rows(paths.DROPPED_PUBMED) + paths.read_rows(paths.DROPPED_LENS)
    fields = list(rows[0].keys())
    print(f"dropped records (both sources): {len(rows)}")

    near = [r for r in rows if r["soft"] and r["dom"] and not r["meth"]]
    print(f"\n1. NEAR-MISS (software + domain, no inference term): {len(near)}")

    sweep = [r for r in rows
             if title_cue(r["title"]) and hits(r["title"].lower(), DOM)]
    print(f"2. PACKAGE-TITLE SWEEP (title cue + epi signal): {len(sweep)}")

    nocue = [r for r in rows if not title_cue(r["title"])]
    random.seed(SEED)
    sample = random.sample(nocue, min(SAMPLE_N, len(nocue)))
    print(f"3. NO-CUE STRATUM: {len(nocue)}; seeded random sample: {len(sample)} "
          f"(seed={SEED})")

    paths.write_rows(paths.RECALL_NEARMISS, sorted(near, key=lambda r: r["title"]), fields)
    paths.write_rows(paths.RECALL_TITLESWEEP, sorted(sweep, key=lambda r: r["title"]), fields)
    paths.write_rows(paths.RECALL_SAMPLE, sample, fields)
    print(f"\nwrote {paths.RECALL_NEARMISS.name}, {paths.RECALL_TITLESWEEP.name}, "
          f"{paths.RECALL_SAMPLE.name}")

    return {"audited": len(rows), "nearmiss": len(near), "titlesweep": len(sweep),
            "nocue_stratum": len(nocue), "random_sample": len(sample),
            "random_sample_seed": SEED}

