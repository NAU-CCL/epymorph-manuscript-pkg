# epymorph-manuscript-pkg

Reproducibility package for the epymorph manuscript: data, analysis code and manuscript
source in one repository with one git history, following FAIR4RS principles.

The goal it is built to: **nothing in the manuscript asserts a number the code cannot
reproduce.** Every figure, table and quoted count is generated, and `just check` fails if
any of them stops agreeing with the code that produces it.

The layout is meant to be generic. Any future project of "a Python analysis plus a
manuscript" could reuse it.

---

## How this repository works

Four layers, and **what writes a file decides where it lives.** That one rule explains
every directory here.

| | written by | in git | safe to delete |
|---|---|---|---|
| `data/` | nobody. Archived evidence, never modified. | yes | **no** |
| `analysis/` | a human, editing code | yes | no |
| `manuscript/` | a human, via Overleaf | yes | no |
| `results/` | the build, only | mostly (see below) | **yes**, rebuilt |

`results/` is the one that matters in practice: if you are unsure whether a file is
precious, ask whether the build wrote it. Everything under `results/` can be deleted and
rebuilt, so nothing there should ever be hand-edited.

### The exception: the runs

Each case study compares three models, and each model is fitted and forecast over a whole
season at two random seeds. One model at one seed is a **run**; there are twelve.
`results/demos/runs/` holds them: 1.02 GB, one file of 114 MB, so **git does not carry
it**. It is the only generated thing that cannot be rebuilt on a whim: fitting all twelve
takes about five hours. `results/demos/README.md` says how to rebuild or fetch them, and
what `runs.sha256` beside them means.

Everything needed to *check the paper* is in git without them: the figures, the tables,
and the frozen observations they were computed from.

---

## The workflow

The commands are recipes in the `justfile` ([just](https://just.systems):
`brew install just`). Each is one or two lines, readable there if you would rather not
install it.

### 1. Set up, once

```bash
just setup                    # uv sync in analysis/, and a .env from .env.example
```

No API key is needed to build or check anything. Every external input is frozen in the
repository: the CDC surveillance series in `data/demos/` (they are revised weekly, so
re-fetching would move the target the models are scored against), and the Census
demography, commuting and contact-matrix inputs in `data/raw/`, each with a provenance
record. epymorph downloads Census TIGER geography once per machine, which needs no key. A
free Census API key, in `.env`, is needed only to refresh a frozen input deliberately.

### 2. Build everything the manuscript uses

```bash
just build                    # minutes with the runs on disk; about 5 h without them
```

Runs the literature search, then each case study's notebook through papermill. A run
already on disk is reused and a missing one is fitted, so on a fresh clone this is the
slow half of the analysis; an interrupted build resumes rather than starting over. To skip
the fitting, fetch the archived runs first (see `results/demos/README.md`).

Writes `results/lit-search/`, `results/demos/figures/` (six figures),
`results/demos/tables/` (six tables, each as a `.csv` to read and a `.tex` to `\input`),
the executed notebooks `results/demos/demo-*.ipynb`, and `results/checksums.sha256`.

### 3. Check it

```bash
just check                    # about 4 minutes
```

Rebuilds what can be rebuilt in minutes and compares it with what is committed:

- every generated `.tex` still carries its `% GENERATED` header;
- the literature search's own eight checks, including that every count the manuscript
  quotes from it matches;
- `results/` against `results/checksums.sha256`;
- the runs against `results/demos/runs.sha256`;
- both notebooks rerun into a scratch folder: tables byte for byte, figures pixel for
  pixel (within 2/255, the antialiasing noise matplotlib's drawing carries from one
  process to the next).

The last two are skipped, with a message, when the runs are absent.

### 4. Publish the generated files to Overleaf

```bash
just publish                  # report
just publish --apply          # copy, then verify
```

Then, in the Overleaf clone: `git add -A && git commit && git push`, and click **Pull**
in Overleaf's GitHub panel.

### 5. Read or explore the analysis

```bash
just notebooks
```

Each case study is one notebook, read top to bottom: it builds the models, explains one
fit and forecast, makes the runs, and scores them into the figures and tables. Opened
interactively it shows its figures and tables without writing them.

---

## What is here

```
data/
  demos/{flu,covid}/observations.csv   frozen surveillance. Cannot be re-derived.
  raw/                                 Census and contact-matrix inputs, with provenance
  lit-search/raw/                      archived search exports
  lit-search/decisions/                hand-entered screening calls
analysis/
  pyproject.toml, uv.lock              one uv environment
  manuscript_analysis/
    __main__.py                        the build: the search, then each notebook
    demo-flu.ipynb, demo-flu.md        Demo 1, and what to know about it
    demo-covid.ipynb, demo-covid.md    Demo 2, likewise
    *_inputs.py, runs.py, scoring.py, plots.py, util.py, data.py
                                       what the notebooks use that is not epymorph
    lit_search/                        the software-landscape search pipeline
manuscript/         LaTeX, one file per section; round-trips with Overleaf
results/            organised by producer, mirroring data/
  checksums.sha256  everything the build writes, except the runs
  demos/figures/    the manuscript's figures
  demos/tables/     the manuscript's tables, .csv and .tex
  demos/runs/       the runs. NOT in git; demos/runs.sha256 vouches for them
  lit-search/       shortlists, register, PRISMA flow, Table 1
scripts/            check.py, sync-manuscript.sh, publish-results.sh, build-docx.sh
justfile            setup, build, check, notebooks, publish, ...
```

`analysis/README.md`, `results/demos/README.md`, `data/raw/README.md`, `scripts/README.md`
and the search pipeline's own README have the detail.

### The two analyses

**The software landscape** (`lit_search`) surveys comparable packages: a structured search
of PubMed and Lens.org, a keyword screen, a recall audit of what the screen set aside, and
Table 1. Its checks include that Appendix S1's fourteen quoted counts match the pipeline,
that §S1.1 lists every term the screen runs on, that Table 1 is a faithful projection of
the decisions behind it, and that the archived exports have not changed.

**The two case studies** ask one question of different added structure: *does it buy
forecast skill?* Demo 1 (`demo-flu`, influenza in 51 jurisdictions) asks it of age
structure; Demo 2 (`demo-covid`, COVID-19 in three New England states) of spatial
structure and movement. Within each, the three models differ only in data, never in code,
which is the claim the manuscript rests on.

---

## Keeping the manuscript in step

The manuscript is edited in Overleaf, which round-trips with the separate
`epymorph_ms_overleaf` repository. `just sync-manuscript` (`scripts/sync-manuscript.sh`)
mirrors it one way into `manuscript/` here: it reports by default, copies with `--apply`,
verifies byte-equality afterwards, and refuses when a file is newer here than in Overleaf.

Generated figures, tables and numbers travel the other way, via `just publish`
(`scripts/publish-results.sh`).

**The two are not a bidirectional sync.** They are two one-way mirrors over **disjoint
sets of files**, which is what makes the arrangement safe:

| | written by | direction |
|---|---|---|
| `main.tex`, `supplement.tex`, `sections/`, `supplementary/`, `references.bib` | a human, in Overleaf | Overleaf -> here |
| `figures/`, `tables/`, `manuscript-numbers.tex` | this repository's build | here -> Overleaf |

No file is ever written by both sides, so neither can lose an edit the other made.
`publish-results.sh` additionally warns when a generated `.tex` in Overleaf has lost its
`% GENERATED` header, which is what a hand-edit looks like from the outside.

**Never hand-edit a generated table**, in either repository; `just check` catches it here,
and the publish script's warning catches it there.

The manuscript includes them the usual way:

```latex
\includegraphics[width=\textwidth]{figures/fig2-flu-demographic-structure.pdf}
\input{tables/flu-skill}
```

---

## Still to come

- **A from-scratch rebuild.** Individual runs have been reproduced byte for byte (the full
  season of one model per case study, and the first three forecast dates of all six), but
  the twelve have not yet been rebuilt together from an empty folder and compared with
  `runs.sha256`.
- **An archive for the runs**, with a `.zenodo.json`, so a clone can fetch them rather
  than spend five hours fitting.
- **`results/manuscript-numbers.tex`**: generated `\newcommand` macros, so the prose quotes
  numbers rather than typing them.
- **A compiled PDF from the build**, plus the "flatten to one file" step Springer Nature's
  submission format wants (see `manuscript/README.md`).
- **A container** (`just build-docker`), so the build does not depend on the machine.

---

## License

Two licenses, matching two kinds of content:

- **Code** (`analysis/`): GPL-3.0-only, see `LICENSE`. Matches epymorph itself
  (NAU-CCL/Epymorph, GPL-3.0), which the analysis depends on.
- **Manuscript text and figures** (`manuscript/`, `results/demos/figures/`): CC BY 4.0, see
  `LICENSE-MANUSCRIPT.md`.

## Citation

See `CITATION.cff`.
