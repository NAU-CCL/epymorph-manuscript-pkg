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
manuscript/                            LaTeX, optionally synced with Overleaf
  generated/                           generated figures and tables copied for the manuscript
results/
  demos/figures/, demos/tables/        the manuscript's figures and tables
  demos/demo-*.ipynb                   the notebooks as last executed by the build
  demos/runs/                          the model runs (NOT in git; see below)
  lit-search/                          the software search's outputs, Table 1, Figure S1
  checksums.sha256                     everything the build writes, except the runs
scripts/                               scripts to check results and export the manuscript to Word
justfile                               commands for working with the project
```

Never hand-edit anything under `results/` or `manuscript/generated/`.
Every generated `.tex` carries a `% GENERATED` header, and `just check` fails if one is missing.

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

For convenience and ease of collaboration, the manuscript can be edited in
Overleaf. We provide some utilities in the project to make it easy to
synchronize work between this project (on your development machine) and the
Overleaf project.

To set up the Overleaf integration, you will need to authenticate your git
client to Overleaf using an API token. Manage tokens in your
[Overleaf account settings](https://www.overleaf.com/user/settings)
(under "Project synchronization, Git integration").
[See the Overleaf docs for more info.](https://docs.overleaf.com/integrations-and-add-ons/git-integration-and-github-synchronization/git-integration/git-integration-authentication-tokens)
To avoid having to enter this password repeatedly, you may wish to install
[Git Credential Manager](https://github.com/git-ecosystem/git-credential-manager/blob/main/docs/install.md)
(GCM) to securely cache the token.

After setting up authentication, find your project's git integration URL.
Go to your Overleaf project and navigate to its Integrations tab. Click on
**Git** (not GitHub!) and a dialog will pop up displaying a command like
`git clone <url>`. Copy just the URL part. Then in this project run the command
`just setup-overleaf <url>`, replacing the placeholder with the URL you copied.

That completes the setup. Now, any time you've made changes to the manuscript
either in this project or in Overleaf, you may synchronize by running the
command `just overleaf-sync`. This does not happen automatically: you must
decide when you wish to sync. Only files in the `manuscript` folder are
included in the sync, and `manuscript/generated` files only sync one-way:
generated files are pushed to Overleaf, but never pulled from Overleaf. These
files are supposed to be generated entirely by code and require no hand-editing!
The sync command will create a git commit in this project if there are changes
from Overleaf. To help ensure the sync goes smoothly, our recommendation is to
try to perform syncs from a clean working tree (i.e., there are no uncommitted
changes and `git status` reports "nothing to commit").

You may also have collaborators that prefer to comment using Microsoft Word.
`just docx` builds a copy of the manuscript to a Word document and saves it in
`results/manuscript-docx/` (which does not get included in git commits.)
You must have [pandoc](https://pandoc.org) 3.x installed. The Word file can be
then shared for comment however you prefer, but naturally comments and changes
made in Word will need to be copied back into the manuscript by hand.

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
