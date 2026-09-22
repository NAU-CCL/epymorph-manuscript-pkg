# Queries as executed

What was typed into each database, when, with what filters, and how many records came back.
**Appendix S1 §S1.1 is the protocol** and carries the search vocabulary, the inclusion and
exclusion criteria, and the screening method. This file is the receipt for the two archived
exports: the platform-specific syntax, field scopes and filters that §S1.1 summarises but does
not reproduce. Nothing here restates the term lists.

Without this file the screen is reproducible only from the exports onward. Everything in
`scripts/` operates on `lens-export-15july2026c.csv` and `csv-epidemicOR-set-pubmed.csv`; this
is the record of where those two files came from.

**Verification date: 2026-07-15** for both databases.

---

## Lens.org

**Recorded 2026-09-18 from JM's Lens.org account.** Verbatim, as Lens renders it.

**Records returned at export: 1,009** (663 journal articles, 298 preprints, 48 conference
proceedings articles; 97.5% carrying abstracts; publication years 2020-2026). This is the
`lens-export-15july2026c.csv` in this directory, and every one of those figures is
reproducible from that file.

### Scope

Four fields, each carrying the full `A AND B AND C` expression, combined with `OR`:
**Title**, **Abstract**, **Keyword**, and **Field of Study**.

### Filters

```
Year Published  = ( 2020 - )
Publication Type = ( preprint, journal article, conference proceedings article )
```

### Query

```
( Title: ( ( epidemic OR ( epidemiological OR ( "infectious disease" OR ( "disease
transmission" OR ( compartmental OR ( metapopulation OR ( meta-population OR state-space
) ) ) ) ) ) ) AND ( ( "particle filter" OR ( "sequential Monte Carlo" OR ( SMC OR (
"ensemble Kalman" OR ( "Kalman filter" OR ( "data assimilation" OR ( "partially observed
Markov" OR ( Bayesian OR ( "Markov chain Monte Carlo" OR ( MCMC OR ( "approximate
Bayesian computation" OR ( ABC OR ( "uncertainty quantification" OR ( calibration OR
inference ) ) ) ) ) ) ) ) ) ) ) ) ) ) AND ( software OR ( package OR ( library OR (
toolkit OR ( "R package" OR "Python package" ) ) ) ) ) ) )
OR ( Abstract:        [ the same A AND B AND C expression ] )
OR ( Keyword:         [ the same A AND B AND C expression ] )
OR ( Field of Study:  [ the same A AND B AND C expression ] )
```

The vocabulary itself is not repeated here. Appendix S1 §S1.1 lists the three blocks,
and the nested expression above is the same vocabulary as Lens renders it.

### Two notes for the appendix

**1. The appendix's reported search string is verbatim-correct.** Every term in all three
blocks of §S1.1 appears in the executed query, in the same blocks, with nothing added or
dropped. This was worth checking and it came back clean.

**2. The field scope is now stated in §S1.1, and it was always negligible.** The appendix
once described Lens as scoped to title/abstract/keywords; it now names all four fields. The
difference never mattered: re-applying `A AND B AND C` locally against the export, 820 of the
1,009 records satisfy it within title/abstract/keywords and a further **7** only once Field of
Study is included, so the fourth field accounts for about 0.7% of the retrieval and changed
nothing downstream. (The remaining 182 are the limit of the local test rather than a finding:
Lens applies its own stemming and phrase matching, which a literal regex does not reproduce.)

### Why re-running it today gives a different number

Lens reports **1,067** scholarly works for this query as of 2026-09-18, against the **1,009**
exported on 2026-07-15. **Confirmed by JM: the 1,009 is the July figure and the 1,067 came
from an accidental re-search today.** The +58 is two months of index growth on a 2020-onward
query whose two most recent years are its largest strata (2025: 192, 2026: 190). It is not
truncation: 1,009 already exceeds the 1,000-record free-account cap.

**1,009 is the number Appendix S1 reports and it is correct.** Anyone re-running this query
later will see a larger count, and that is expected rather than a discrepancy.

---

## PubMed

**Reconstructed 2026-09-18 and verified by reproduction.** No saved search survived: the
search was run at the time by Claude, `project-notes/` predates this work and never mentions
it, and PubMed's own history was not captured. The query below was rebuilt from the §S1.1
concept blocks and then **tested against the archived export**, which is a stronger check than
a remembered string.

**Records returned at export: 2,403**, of which **2,364 carry abstracts** and are the screened
set. Retrieval date 2026-07-15, fixed by the latest Create Date in the export.

### Query

Three concept blocks, all fields (no field tags), with a publication-date filter. The blocks
are identical to Lens's, which is the point of §S1.1's "the same query was run on Lens.org".

```
(epidemic OR epidemiological OR "infectious disease" OR "disease transmission" OR
 compartmental OR metapopulation OR "meta-population" OR "state-space")
AND
("particle filter" OR "sequential Monte Carlo" OR SMC OR "ensemble Kalman" OR
 "Kalman filter" OR "data assimilation" OR "partially observed Markov" OR Bayesian OR
 "Markov chain Monte Carlo" OR MCMC OR "approximate Bayesian computation" OR ABC OR
 "uncertainty quantification" OR calibration OR inference)
AND
(software OR package OR library OR toolkit OR "R package" OR "Python package")
AND 2020:3000[dp]
```

### The verification, and what it does and does not prove

Run through the NCBI E-utilities `esearch` endpoint on 2026-09-18:

| | |
|---|---|
| Reconstructed query, today | **2,524** records |
| Archived export, 2026-07-15 | **2,403** records |
| Export PMIDs also returned today | **2,403 — 100.00%** |
| Export PMIDs *not* returned today | **0** |
| New since the export | 121 |

**Every single archived record is returned by this query**, and the excess is +5.0% over two
months, which matches the +5.8% seen on the Lens side over the same interval. Three further
things corroborate the form:

- **The download filename.** PubMed names a download after the query's first term, and the
  file is `csv-epidemicOR-set-pubmed.csv`, so the executed query opened `epidemic OR ...` —
  exactly how block A opens.
- **It was not field-tagged.** The same query with `[tiab]` on every term returns **281**
  records today, two orders of magnitude short of 2,403, so the search ran across all fields.
- **The export format is the web interface's.** The CSV columns (`Journal/Book`, `NIHMS ID`,
  `Create Date`) and the MEDLINE-style abstract text file are PubMed's website Save formats,
  not E-utilities output.

**What this proves:** the recorded query retrieves the archived set exactly, so the screen is
reproducible end to end from this file forward. **What it does not prove:** that the string is
character-identical to what was typed in July. An equivalent query could return the same set.
The appendix should therefore describe this as the query *verified to reproduce the archived
records*, not as one recovered from search history. That is an honest and, for a structured
search, a sufficient claim.

### The 2019 record is not an anomaly

Resolved while checking the above. PMID 31685541 shows `Publication Year` 2019 in the CSV but
is `Br J Gen Pract. 2019 Dec 26 ... Print 2020 Jan` — an electronic-ahead-of-print. PubMed's
`[dp]` sees 2020, so the date filter behaved correctly; only the export column's year is
misleading. No footnote needed in the appendix, and nothing to fix.

## Other sources

The registry and citation-chaining legs are **discovery** sources, not counted retrieval, and
Appendix S1 §S1.8 reports them by the packages they surfaced rather than by record count. They
are listed there, not here, because a curated task view or a reference list has no denominator
to report.

_Both queries recorded 2026-09-18: Lens verbatim from JM's account, PubMed reconstructed and
verified to return 100% of the archived export. Decision 2 of `refactor-plan-v01.md` is the
only thing still open in this directory._
