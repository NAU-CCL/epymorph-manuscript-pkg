# epymorph-manuscript-pkg

Reproducibility package for the epymorph manuscript: data, analysis code and manuscript
source in one repository.

This file covers the repository as a whole. `analysis/README.md` covers the analysis code.

## Layout


| directory | written by | in git | safe to delete |
|---|---|---|---|
| `data/` | nobody: archived inputs, never modified | yes | **no** |
| `analysis/` | a person, editing code | yes | no |
| `manuscript/` | a person, in Overleaf | yes | no |
| `results/` | the build, only | yes, except the runs | **yes**, the build rewrites it |
| `scripts/` | a person, editing code | yes | no |

```
data/
  demos/{flu,covid}/observations.csv   frozen CDC surveillance series
  raw/                                 frozen Census and contact-matrix inputs, each with a
                                       .provenance.json
  lit-search/raw/                      archived PubMed and Lens.org exports
  lit-search/decisions/                hand-entered screening decisions
analysis/                              the Python package and both case-study notebooks
manuscript/                            LaTeX, mirrored from Overleaf
results/
  demos/figures/, demos/tables/        the manuscript's figures and tables
  demos/demo-*.ipynb                   the notebooks as last executed by the build
  demos/runs/                          the model runs (NOT in git; see below)
  lit-search/                          the software search's outputs, Table 1, Figure S1
  checksums.sha256                     everything the build writes, except the runs
scripts/                               check.py, Overleaf sync and publish, Word export
justfile                               every entry point
```

Never hand-edit anything under `results/`. Every generated `.tex` carries a `% GENERATED`
header, and `just check` fails if one is missing.

## Quick start

`just` commands in the `justfile` ([just](https://just.systems)) are used to execute code:

```bash
just setup        # install the pinned environment (uv) and create .env
just build        # build every result: minutes with the runs on disk, ~5 h without
just check        # rebuild and compare with what is committed: ~4 min
just notebooks    # open the case-study notebooks in JupyterLab
```

You don't need an API key to build or check anything, because every external input is
frozen in `data/`. A Census API key in `.env` is needed only to refresh a frozen input on
purpose.

`just check` determines if all the elements pass reproducibility, so run it before and after a change. It checks:

- the `% GENERATED` headers;
- the literature search's eight checks, including that every count the manuscript quotes
  from it matches the pipeline;
- `results/` against `results/checksums.sha256`;
- the runs against `results/demos/runs.sha256`;
- both notebooks, rerun into a scratch folder: tables byte for byte, figures pixel for
  pixel (within 2/255, to allow for matplotlib's antialiasing noise).

The last two are skipped, with a message, when the runs are missing.

## The runs

Each case study compares three models, each fitted and forecast over a season at two
random seeds. One model at one seed is a **run**, so there are twelve. They live in
`results/demos/runs/<demo>/seed<N>/<model>/`, and these are git ignored: together they
are 1 GB, and one file is larger than GitHub's 100 MB limit. Building all twelve from
scratch takes about five hours, if you run four at a time. The build reuses a run already on disk.

You don't need the runs to check the paper. The figures, the tables and the observations
they were computed from are all in git.

`results/demos/runs.sha256` records the runs the manuscript used. To replace the reference runs
deliberately, delete the files and build. A fixed seed reproduces a run byte for byte on
the same platform, but on different hardware, expect this checksum check to fail.

Every build rewrites `results/demos/demo-*.ipynb`, and papermill's timing metadata alone
makes git see a change. Commit them only when the analysis changes; otherwise run
`git restore results/demos/*.ipynb`.

## The manuscript and Overleaf

The manuscript is written in Overleaf, which syncs with a separate git repository (the
"Overleaf clone"). The scripts find it at `../epymorph_ms_overleaf`, next to this
repository; set `OVERLEAF=/path/to/clone` to use another location.

Two one-way mirrors move files between the two repositories. They cover **disjoint sets of
files**, so no file is ever written on both sides:

| files | written by | direction | recipe |
|---|---|---|---|
| `main.tex`, `supplement.tex`, `sections/`, `supplementary/`, `references.bib`, `figures/fig1-*` | a person, in Overleaf | Overleaf → `manuscript/` | `just sync-manuscript` |
| every other figure, the tables | this repository's build | `results/` → Overleaf | `just publish` |

Both recipes only report what they would change. Add `--apply` to copy. After
`just publish --apply`, commit and push in the Overleaf clone, then click **Pull** in
Overleaf's GitHub panel. Edit prose in Overleaf, not in `manuscript/`: the next sync would
overwrite it.

`just docx` builds Word copies of the manuscript and supplement from the Overleaf clone,
for collaborators who comment in Word. It needs [pandoc](https://pandoc.org) 3.x and
writes them to `results/manuscript-docx/`, which is not in git. Comments made in Word are
copied back into Overleaf by hand.

Notes on the LaTeX:

- The template is Springer Nature's `sn-jnl.cls`. Its submission system wants a single
  `.tex` file with the references pasted in, so we draft one file per section and will
  flatten them at submission.
- `supplement.tex` is a separate document. In Overleaf, compile it with
  Menu > Main document.
- `references.bib` is a Zotero export with small patches: `file = {...}` lines removed,
  and `mckinney_data_2010` recast as `@article`, because `sn-nature.bst` fails on an
  `@inproceedings` that has no editor.

## Still to come

- An archive of the runs (Zenodo), so a fresh clone can fetch them instead of spending
  five hours fitting.
- `results/manuscript-numbers.tex`: generated `\newcommand` macros, so the prose quotes
  numbers rather than typing them.
- A compiled PDF from the build, and the flatten-to-one-file step for submission.
- A container, so the build does not depend on the machine.

## License

- **Code** (`analysis/`, `scripts/`, `justfile`): GPL-3.0-only, see `LICENSE`. This
  matches epymorph, which the analysis depends on.
- **Manuscript text and figures** (`manuscript/`, `results/demos/figures/`): CC BY 4.0,
  see `LICENSE-MANUSCRIPT.md`.

## Citation

See `CITATION.cff`.
