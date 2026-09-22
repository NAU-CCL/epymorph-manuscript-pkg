# screen-decisions.csv — codebook

What every column means and what may go in it. **645 rows**, one per record the pre-filter
advanced (437 PubMed, 208 Lens), sorted so the work comes first.

You edit **`decision` and `reason`**, and optionally `status`. Everything else is evidence
the pipeline computed; overwriting it will be silently undone on the next run, because
`src/screen.py` recomputes those columns from `data/` and only joins your two back on.

`src/validate_decisions.py` checks this file against the vocabularies below on every
`run_all.py`, so a typo or a value not listed here is reported rather than absorbed. **The
lists in this document are what it reads** — the bullet format matters, so add a value here
first and it becomes legal.

---

## Columns you fill in

### `decision` — the disposition. Required.

- `Include - Table 1` — a tabulated package, one of the twelve columns of Table 1
- `Include - capsule` — a real package, described in §S1.4 but not tabulated
- `Include - context` — recorded as context in §S1.5; adjacent, not a comparator
- `Reference (cite)` — not software; cited for the discussion or the methods
- `Exclude` — out of scope

### `reason` — why, in a short phrase naming the *class*. Required when `decision` is set.

Not a sentence, and not a summary of the paper. The convention is a class, optionally
followed by a colon and the specific. Four families cover all 582 filled rows:

**1. Out of scope.** The workhorse: 397 of 645 rows are the first of these. The class after
the colon must be one of:

- `not a mechanistic epidemic-forecasting software package` — the catch-all
- `clinical prediction model`
- `evidence synthesis, not software`
- `phylogenetics or genomics tool`
- `health economics, not software`
- `clinical or field study, not software`

written as, for example, `Out of scope: clinical prediction model`.

**2. Already in register.** The record is an application or citation of a package already in
the candidate register, so it is not new software. Any of these shapes:

`Already in register` · `Already in register (pomp)` ·
`Already in register / mentions known package: surveillance`

The third form is what rule `R1` writes, taking the name from the `known` column. Use the
display name as `known` spells it, so the two agree.

**3. A named near-miss.** `<name>: <what it is and why it is out>`, for records that needed a
real judgement. For example
`eSIR: Bayesian hierarchical SIR forecasting toolbox (R); single-population`.

**4. A method, not a package.** `<description>; not a package`, or `; method, not a package`.
For example `Bayesian workflow/benchmark for compartmental models; not a standalone package`.

### `status` — your progress marker. Optional; nothing depends on it.

- `NEEDS YOUR CALL` — read the record, write a decision and a reason (3 rows)
- `proposed` — a decision is pre-filled. Confirm it, or overwrite it (207 rows). Two
  things produced these: a rule fired (see `rule`), or the 2026-09-21 sweep read the abstract
  and dispositioned it (those rows have a blank `rule`).
- `carried` — the first pass already decided this. Leave alone unless you disagree (435 rows)
- `confirmed` — use this to mark rows you have checked, if you want to track progress

---

## Columns the pipeline computes

Do not edit these. `src/screen.py` regenerates them from `data/` on every run.

| column | what it is |
|---|---|
| `rule` | which pre-fill rule produced the proposed decision, or `first pass` if the decision was carried from the original screen. See the table below. |
| `source` | `PubMed` or `Lens` — which database export the record came from |
| `id` | PMID for PubMed rows, Lens record ID for Lens rows. Unique; the join key together with `source`. |
| `year`, `title`, `venue`, `doi` | as the export gave them. `venue` is blank for 46 rows and `doi` for 22; that is the export's gap, not an error. |
| `type` | `journal article` (549), `preprint` (87), or `conference proceedings article` (9) |
| `soft`, `meth`, `dom`, `filt` | lexicon match counts. See below. |
| `known` | which register packages the record mentions, by display name, `;`-joined (e.g. `EpiEstim;EpiNow2`). Blank for 598 rows. |

### `rule` — why a decision was proposed

- `first pass` — carried from the original screen; no rule fired
- `R1 names a register package` — the record mentions a package already in the register, so it is an application or a citation, not new software
- `R2 title exclusion` — the title places it in a documented excluded class: clinical prediction model, evidence synthesis, health economics, phylogenetics/genomics, pharmacokinetics, clinical or field study
- `R3 no software cue in title` — no package name, no CamelCase or dotted token, no "package/toolkit/library/framework". A released package almost always names itself in its title.
- `R4 already reported in S1.9` — the appendix already reports this record by name, so its disposition is fixed by what the manuscript says

### `soft`, `meth`, `dom`, `filt` — how many lexicon terms matched

Each is a **count of distinct patterns** from one block of `src/lexicon.py` that matched the
record's title plus abstract. They are evidence for triage, not scores, and nothing is
decided by their size.

| column | block | counts terms for | range here |
|---|---|---|---|
| `soft` | `SOFT` (block A) | software or artifact: *package, software, toolkit, library, framework* … | 1–10 |
| `meth` | `METH` (block B) | inference: *particle filter, sequential Monte Carlo, ensemble Kalman, Bayesian, calibration, parameter estimation* … | 1–6 |
| `dom` | `DOM` (block C) | epidemiological domain: *epidemic, outbreak, transmission, infection* … | 1–8 |
| `filt` | `FILT` (a subset of B) | sequential filtering specifically | 0–3 |

**Every row has `soft` ≥ 1, `meth` ≥ 1 and `dom` ≥ 1**, because a record only advances to this
file if all three blocks fire (`advances()` in `src/screen.py`). A count of 1 therefore means
"the minimum to get here", not "a weak match" in any absolute sense.

**`filt` is the useful one for triage.** It is reported separately and is *not* an inclusion
gate, so a high `filt` is the strongest single hint that a record might be a
sequential-filtering package. Rows are sorted by `filt` descending, then `soft` descending.

**Four rows with `filt = 1` are false positives**: they match `SMC` as *seasonal malaria
chemoprevention*, not sequential Monte Carlo. Do not let the count mislead you.

---

## Fixed on 2026-09-21

Both recorded here because the repair changed the hand-entered layer, which has no version
control, and a snapshot of the previous state was kept.

**1. `decision` had six values where the vocabulary had five.** Four `carried` rows from the
first pass said `Context` instead of `Include - context`. Normalised, so `Include - context`
now covers 7 rows and the vocabulary above is exhaustive. The validator will reject `Context`
from now on.

**2. `known` held regex patterns, not package names.** Cells read `\bhmer\b` and
`\bpomp\b(?! )` because the column was `";".join(hits(blob, KNOWN))` over a list of
patterns. `src/lexicon.py` now carries `KNOWN` as `(display name, pattern)` pairs and
`src/screen.py` emits the names, so cells read `hmer` and `pomp`. **The repair was gated on
matching being unchanged**: every one of the 645 rows keeps the same match presence and the
same number of matches, so only the rendering moved. One `reason` that had copied the debris
(`... mentions known package: pomp\b(?! )`) was cleaned, and nine more had their package
names case-corrected to the display spellings.

**3. Fifty exclusions rested on evidence the lexicon no longer reproduced.** The first pass
matched bare `surveillance` and bare `dust` as register-package mentions and excluded 50
records with `Already in register / mentions known package: ...`. The lexicon was later
tightened to `\bsurveillance package\b` and `\bR package surveillance\b`, and the reasons
did not follow, so those records cited a match the pipeline no longer finds. All 50 were
re-read against their abstracts: 47 are out of scope on their merits and now carry the right
class, and **three were handed back as `NEEDS YOUR CALL`** because they are genuinely
arguable (see the handoff note). One further row cited two packages where only one still
matches, and now cites only that one.

`src/validate_decisions.py` gained the check that would have caught this: **a reason of the
form `mentions known package: X` must have a non-empty `known`, and the names must
intersect.** `known` is recomputed from `data/` on every run while `reason` is frozen when a
human writes it, so this is the one place where a stated rationale can silently outlive its
evidence.

## Checking your work

```
python3 run_all.py            # regenerates results/, validates this file
python3 src/validate_decisions.py   # just the validation
```

The same `decision` vocabulary governs the `Decision` column of `packages.csv`, and the
validator holds the register to it too.

The validator reports: rows with a `decision` but no `reason` (or the reverse), any
`decision`, `status` or `rule` value not listed above, any `Out of scope:` reason whose class
is not one of the six, any reason citing a package mention that `known` no longer supports,
and how many of the 645 rows carry a disposition. `src/screen.py`
prints that last count on every run too, so progress is visible without opening the file.

When it reads `645/645`, Appendix S1 §S1.1 and §S1.9's claims about per-record dispositions
are true as written.
