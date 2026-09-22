# decisions/ — the only files a human edits

Nothing in this directory is ever written by a script. The two seeding scripts
(`src/seed_decisions.py`, `src/tables.py --seed`) each created their file once and
**refuse to overwrite it**, and `src/screen.py` joins these decisions on without being
able to write back. So a re-run can never destroy a hand-entered call.

`results/` is the opposite: regenerated on every run and always safe to delete.
`data/` is never written by anything. Those three rules are the directory layout.

## screen-decisions.csv

One row per record the pre-filter advanced: **645 rows**, the 437 PubMed and 208 Lens records
reported in Appendix S1 §S1.9. Sorted so that the work comes first.

### Fill in `decision` and `reason`. Nothing else.

**`screen-decisions-codebook.md` in this directory defines every column and lists what may
go in it** — the decision vocabulary, the `Out of scope:` classes, the rule codes, and what
the `soft`/`meth`/`dom`/`filt` counts actually count. Read that rather than reconstructing the
vocabulary from the rows. `src/validate_decisions.py` reads its lists straight out of that
document and checks this file against them on every `run_all.py`, so a typo is reported
rather than absorbed; `run_all.py --check` makes it fail the build.

The other columns are there so you can judge without opening a second file, and the codebook
says what each one is. The one worth knowing before you start: **`filt` counts
sequential-filtering terms specifically**, so a high `filt` is the strongest single hint that
a record might be a filtering package, and the rows are sorted by it.

### How much work is left

| status | rows | what to do |
|---|---|---|
| `NEEDS YOUR CALL` | **3** | Read the record, write a decision and a reason. |
| `proposed` | 207 | Pre-filled by a rule or by the 2026-09-21 abstract sweep. Confirm, or overwrite. |
| `carried` | 435 | The first pass already decided this. Leave alone unless you disagree. |

Change `status` to `confirmed` as you go if you want to track progress; nothing depends on it.
The decision and reason vocabularies are in the codebook, not repeated here.

### The rules behind the 144 proposals

Each proposed row names its rule in the `rule` column, so a reviewer can see why a record was
set aside rather than only that it was.

| rule | what it fires on |
|---|---|
| `R1 names a register package` | the record mentions a package already in the register, so it is an application or a citation, not new software |
| `R2 title exclusion` | the title places it in a documented excluded class: clinical prediction model, evidence synthesis, health economics, phylogenetics/genomics, pharmacokinetics, clinical or field study |
| `R3 no software cue in title` | the title carries no package name, no CamelCase or dotted token, no "package/toolkit/library/framework". A released package almost always names itself in its title, which is the same premise the recall audit's package-title sweep rests on |
| `R4 already reported in S1.9` | the appendix already reports this record by name, so its disposition is fixed by what the manuscript says |

### Four things worth knowing before you start

**All 63 open rows are PubMed.** The Lens leg is fully dispositioned. The gap is exactly the
widening of the PubMed lexicon when the pre-filter was unified: the first-pass PubMed
shortlist was 229 records, the unified one is 437.

**Three rows are pre-filled under R4 and are worth a look first**, because they are the records
§S1.9 already reports as findings and you will want to agree with the appendix or change it:

| PMID | record | proposed |
|---|---|---|
| 39364337 | "A data science pipeline applied to Australia's 2022 COVID-19 Omicron waves" — this is **summer2/estival**, the whole reason the re-screen was worth running | `Include - Table 1` |
| 35187502 | "ARBO: Arbovirus modeling and uncertainty quantification toolbox" | `Include - capsule` |
| 35965465 | "An algebraic framework for structured epidemic modelling" — **AlgebraicJulia** | `Include - context` |

**Most of the 63 are obvious on the title.** They are dominated by clinical and field
epidemiology that the widened inference vocabulary let through: nurse turnover intention,
head-circumference reference charts, dental undergraduates, temporomandibular disorders. The
genuine judgement calls are perhaps eight, and they cluster at the top of the file.

**Four rows carry `filt=1` and are false positives**, so do not let the filter count mislead
you: they match `SMC` as *seasonal malaria chemoprevention*, not sequential Monte Carlo.

### One duplicate the screen did not catch

PMIDs 42038415 (arXiv) and 42234202 (Bull Math Biol) are the same paper, "A Tutorial on
Structural Identifiability of Epidemic Models Using StructuralIdentifiability.jl", indexed
twice. De-duplication only ran PubMed against Lens, never PubMed against itself, so
preprint/journal pairs inside the PubMed export survive. One pair out of 2,364 does not move
any reported number, but give them the same disposition and note it if you want §S1.9 to be
airtight.

---

# table-marks.csv

**One row per package**, 14 rows. Capabilities are columns, marks are **Yes / No / `*`**.
Written with a UTF-8 BOM so Excel and Numbers read it correctly — the earlier long-format
version used the ●◐○ glyphs and they arrived corrupted.

Originally built by `src/tables.py --seed` from the two live drafts. **It no longer matches
them**, by intention: on 2026-09-21 the worksheet was reworked ahead of the drafts (JM
request), so the worksheet is now the proposal and the drafts are what has to catch up. See
"What the drafts still have to absorb" at the end of this section.

- **Table S1**, `drafts/appendix-software-landscape-v02.md` — all 14 packages
- **Table 1**, `drafts/intro-v05.md` — 12 packages and 10 capabilities, exactly as §S1.10
  documents

### The words, and what they mean

`Mixed` is gone. It was hard to interpret — one word covering both "a language feature does
the work" and "part of the capability's scope but not all of it" — and it was carrying too
much: 36 cells had it, including 10 of the 14 in a single row.

| mark | means |
|---|---|
| `Yes` | a dedicated API, construct or data service for the capability |
| `No` | nothing in the package addresses it |
| `*` | a genuinely hard yes/no call. **Every `*` has a row in `table-notes.csv`** saying why, naming the function, dataset or passage it turns on |

A `*` is not a hedge, and it is still not "a user could implement it" — every package here is
programmable, so that would be true of all of them and carry no information. It marks a cell
where the evidence points both ways, and the note says which ways.

The first column, **`Automated data handling`**, is not a mark at all: it **lists the types of
data** the software fetches automatically or ships as reusable model inputs, or `None`. It
replaces the two former rows, `Automated surveillance-data acquisition` and `Automated
population & movement-data acquisition`.

### What counts as automated data handling

The rule (JM decision, 2026-09-21). It is narrower than "ships a dataset" and broader than
"calls an API":

> Count data you would build a **new** model on — population, contact matrices,
> commuting/mobility, surveillance series — and only when the package gives you data for a
> place and time **you** choose: a live service, or a repository covering many regions. A
> fixed historical extract that exists to run the package's own examples does not count.

Nearly every R package here ships example data, so without that second clause the column
would read `Yes` almost everywhere and carry no information. What those packages do ship is
recorded in `table-notes.csv` regardless, so the judgement is visible rather than buried:
see the notes for spatPomp, surveillance, epidemia and SimInf, each of which ships something
substantive and still scores `None`.

### Fill in `verified`, `source_checked` and `notes`

One row per package is the right granularity for the check §S1.1 promises: *"each retained
package's Table S1 feature marks are then verified against its primary documentation."* The
unit of verification is the package, not the cell.

| column | |
|---|---|
| `package`, `language` | which package |
| `in_table_1` | `yes`, or `no (Table S1 only)` for LibBi/rbi and epidemia |
| `primary_ref` | the citation the appendix uses |
| `doi`, `doi_url` | **click `doi_url` to go straight to the source** |
| `Automated data handling` | the types of data fetched or shipped, or `None` -- not a mark |
| the other 9 capability columns | the mark, as Yes / No / `*` |
| **`verified`** | yes / no / changed |
| **`source_checked`** | what you actually read: package site, CRAN/PyPI page, a named function |
| **`notes`** | anything a reviewer would want |

If you change a mark, edit the capability cell in place and say so in `notes`. Note that
"Bayesian / probabilistic calibration & UQ (any method)" is the baseline row and is `Yes` for
every package by construction; it exists in Table S1 only.

### table-notes.csv — one row per justified cell

The sidecar, **44 rows**, long format: `package`, `capability`, `mark`, `note`, `source`,
`source_url`. A single `notes` column in the grid could not hold one note per cell, and the
notes are the substance of the change — a `*` without its note is just `Mixed` again.

It carries every `*`, and also notes on `Yes`/`No` cells where the call was close or the
mark changed. Each `source` says what was actually read, and whether it was the primary
reference or the package's own documentation.

**Written 2026-09-21 from full text, not abstracts.** Eleven of the thirteen primary
references were read as complete text (`pdftotext` on the PDFs; Europe PMC JATS XML for
summer2/estival; medRxiv JATS XML for MetaRVM). Where the primary reference is silent or
out of date, the note falls back to the package's own documentation or source and says so —
`src/tables.py` records the same convention for DOIs.

**The one reference not read: FlepiMoP** (Lemaitre et al. 2024, *Epidemics* 47, 100753).
Paywalled at Elsevier and not in PMC or Europe PMC. Its marks rest on the flepiMoP GitBook
and the `HopkinsIDD/flepiMoP` repository instead. A PDF would let the paper's own account be
checked against the repository's, which matters here: the appendix's "Data are user-supplied"
is what the docs say and what the repository contradicts.

### This file is the source of truth; Table 1 is generated from it

Since 2026-09-21 the chain is one-directional, which is the whole point:

```
decisions/table-marks.csv   you edit this, by hand            (14 packages, Table S1's marks)
        |
        v  src/table1_tex.py  -- asserts the projection holds
results/table-1-maintext.tex  generated, safe to delete       (12 packages, Table 1's rows)
        |
        v  copied by hand when the marks settle
../epymorph-manuscript-pkg/manuscript/sections/01-introduction.tex
```

Table 1 asks **sharper questions** than this worksheet, so that no main-text cell needs a
`*`: the symbolic row is split in two, the data cell becomes one binary row per data type,
and the model-library and multi-strata criteria are tightened. That is a *projection*, not a
disagreement, and `src/table1_tex.py` records it explicitly -- which worksheet column each
main-text row derives from, and how a `*` resolves -- then asserts every derived cell agrees.
Change a mark here and the next `run_all.py` either regenerates Table 1 to match or fails
naming the cells that no longer line up. 13 of Table 1's 16 rows derive this way; the other
three are recorded in that script's `TABLE1_ONLY` with a reason each.

So: **never hand-edit the generated .tex, and never let Table 1 carry a mark this file does
not support.** That was a real failure mode, not a hypothetical -- on 2026-09-21 the
forecasting row was tightened to require scoring without re-testing the cells that were
already `Yes`, which left epymorph claiming a capability it does not have.

### What the manuscript still has to absorb

Nothing outside this directory was changed. Note that the markdown drafts are **frozen**: as
of 2026-09-21 the live copy is the LaTeX in the sibling `epymorph-manuscript-pkg` repo, and
`src/tables.py` still checks `drafts/`, so its "Table 1 and Table S1 agree" result no longer
says anything about the manuscript. `../table-rows-proposal-v01.md` lists the real targets.

Four things have to land there, in Table S1 and (where the package is tabulated) Table 1:

1. **The two data rows collapse into one**, `Automated data handling`, whose cells list data
   types rather than carrying a glyph. §S1.3's legend needs the `*` definition, and the
   data-counting rule above needs stating.
2. **FlepiMoP gains automated data handling and symbolic model specification.** Both tables
   currently say it has neither. The repository's `datasetup/` layer pulls COVID ground truth
   from the Delphi Epidata/covidcast API and influenza truth from CDC FluSight, and ships US
   county populations, US commuting flows and global age structure; its YAML `compartments` /
   `seir: transitions` sections are a declarative model specification. See both notes.
3. **SimInf gains multiple inference families** (`abc`, `pfilter`, `pmcmc` are all
   exported). **The forecasting row is now two columns**, `Forecast generation from a fitted
   model` (9 of 14) and `Forecast evaluation (proper scoring rules)` (2 of 14), because no
   single mark was consistent: the tightened criterion made epymorph's own cell wrong.
   epymorph has generation (`epymorph.forecasting.ForecastSimulator`) but **no scoring** --
   WIS and coverage come from this manuscript's `demolib.scoring`. Only surveillance/hhh4
   and pypfilt/epifx score in-package. JM's call (2026-09-21) is to drop scoring from Table 1
   as duplication of the hubs' own R packages, and keep it in Table S1.
4. **Three rows have criteria built around epymorph's feature set** and star heavily as a
   result: symbolic specification, the model library, and multi-strata composition. The
   forecasting row was the worst of them and has been split, as above. The other three are
   still open — see `../table-rows-proposal-v01.md`, which works each one through to Yes/No
   and carries a compiling main-text table built on the result.

### Where the DOIs come from

`lit/epymorph-2026.bib`, your Zotero export, which is the authority: a DOI in this worksheet
should point at the work the paper cites, not merely at something with the same name. The
`bib_key` column is the BibTeX key, so it doubles as the `\cite{...}` handle.

**It was cross-checked both ways and the check earned its keep.** All 13 tabulated DOIs agree
exactly between the bib and a set curated by hand from the appendix's own References. Run the
other way, **Crossref's top hit is wrong for six of the fourteen**: it prefers the CRAN package
record over the cited article (spatPomp, SimInf), a *peer-review report* over the paper
(odin/dust/mcstate), the medRxiv preprint over the published version (Epydemix), and for
PyRossGeo and epidemia returns something unrelated entirely. So this is a curated lookup
against your bib rather than a live query.

epymorph has no DOI: it is this manuscript.

### Two cross-checks already run, so you do not have to

**§S1.10's consistency claim holds.** Every shared cell agrees between Table 1 and Table S1.

**Every correction recorded in `knowledge-base/related-software.md` is applied in both
tables — with one exception that turned out to be a stale note rather than a missing fix.**
Checked: pomp EnKF Yes, SimInf particle filtering Yes, SimInf multi-inference Mixed,
PyRossGeo particle filtering No, Epydemix multi-strata Yes, pomp symbolic specification No,
spatPomp and odin multi-strata both Mixed. All correct.

The exception was **hhh4 geographic meta-population**, listed there as a knock-on correction
◐→● while both tables carry ◐. The tables are right: the three-tier criterion recorded twenty
lines further down that same file (JM decision, Jul 2026) puts hhh4 in tier 3, because its
coupling is a fitted regression weight and nothing is transported. The stale line has been
struck through and annotated. **No table change needed.**

### Remember there are two appendix drafts

`appendix-software-landscape.md` and `-v02.md` differ only in citation style and carry
identical marks. Any change has to land in both, or the older one silently disagrees.

---

# packages.csv

The candidate register's **55 packages**, lifted out of the Python list literals in
`src/register.py` and verified to match the workbook's `Register` sheet row for row.
Also UTF-8 BOM'd.

The register's own 10 columns, plus four added here: `bib_key`, `doi`, `doi_url`,
`doi_status`.

| `doi_status` | rows | |
|---|---|---|
| `in the manuscript's bibliography` | 29 | matched to `lit/epymorph-2026.bib` |
| `not cited (no bib entry)` | 16 | left blank; see below |
| `no DOI expected (website or repository)` | 10 | Stan, PyMC, Pyro, filterpy, SMCPy, Stone Soup, Starsim, epinet, epiworldR, epymorph |

Your bib lifted this from 18 to 29. Beyond the 13 table packages it supplied bssm, SimBIID,
Pathogen.jl, BayesianFitForecast, Bernadette, MEmilio, EpiModel, SPARSEMODr, EpiILM/EpiILMCT,
QuantDiffForecast, NGSSEML, gemlib, tsgc, and the Dankwa, Wieland and Chaturvedi references.

**The 16 blanks are blank because they are not cited anywhere in the manuscript**, so there is
no bib entry to match: EpiEstim, EpiNow2, tsiR, nosoi, outbreaker2, particles, ParticleDA.jl,
ARBO, epidWaves, SimCOVID, AlgebraicJulia, hmer, UVA-EpiHiper, eSIR, EpiLPS, aghq. All are
capsule, context or excluded packages, and **none is a Table S1 column**, so none blocks the
table verification. They are named in §S1.8's disposition lists as prose rather than as
citations, which is a defensible choice for a landscape survey; filling them in is only worth
doing if you decide any of them should become a real citation.

Matching is deliberately conservative — three gates, strongest first: an identifier already in
the register's reference string (a PLOS e-number), then the package name as a whole word in a
bib title, then author surname plus year. Anything that clears no gate is left blank. Before
your bib arrived I tried Crossref for these and the results were not usable: ARBO resolved to
an entry in an art-biography dictionary, eSIR to a Turkish literature article, tsgc to a
classics review.

### One thing the bib turned up

**Bernadette's citation in the appendix is stale.** §S1.4 and the References cite
Bouranis et al. 2022, arXiv 2211.15229. Your bib has `bouranis_bayesian_2026`,
doi:10.1093/jrsssa/qnaf130 — "Bayesian analysis of diffusion-driven multi-type epidemic
models with applications to COVID-19", in *JRSS Series A*. The preprint has been published.
The worksheet uses the published version; the appendix should be updated to match, in both
drafts.

**Do not hand-edit the .xlsx.** `src/register.py` rewrites the whole workbook from this
file, so a spreadsheet edit is destroyed on the next run. Edit this CSV instead — as of
2026-09-19 it **is** the source of truth, not a worksheet, so your edits reach the
workbook on the next `run_all.py`.

---

# cran-taskview.csv

The register's second sheet: **34 CRAN Epidemiology Task View packages**, each with its
task-view subsection, an in-scope Yes/No/Borderline, and a disposition note. Lifted out of
`src/register.py`'s literals at the same time as `packages.csv` and verified identical.

Same rule as `packages.csv`: edit here, never in the workbook.

---

# How your edits reach the outputs

`python3 run_all.py` from `software-lit-search/`. Specifically:

| you edit | it reaches |
|---|---|
| `screen-decisions.csv` | the `decision` and `reason` columns of `results/shortlist-*.csv` |
| `packages.csv`, `cran-taskview.csv` | `knowledge-base/software-candidate-register.xlsx` |
| `table-marks.csv`, `table-notes.csv` | nothing yet — they are worksheets until the appendix tables are generated from them, and as of 2026-09-21 they deliberately lead the drafts |

`screen.py` prints how many of the 645 carry a disposition every time it runs, so progress
is visible without opening the file:

```
dispositions: 582/645 - 63 still blank in screen-decisions.csv
```

When that reads `645/645 - complete`, Appendix S1 §S1.1 and §S1.9's claims about per-record
dispositions become true as written, and step 4 of `../refactor-plan-v01.md` can close.

---

# Not yet created

`recall-decisions.csv` would do the same for the 101 title-sweep and 100 random-sample
records. Lower priority: §S1.9's claim about those two strata is aggregate ("all reviewed,
zero in scope") rather than per-record, and the answer is uniform, so a batch annotation
covers it. Say the word and the seeding script grows a second output.
