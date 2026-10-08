# scripts

Automation for the pipeline, run from the repository root. Each script's header comment
has the detail; the top-level `README.md` has the workflow they fit into.

| script | what it does | cost |
|---|---|---|
| `run-demos.sh` | fits and forecasts every demo model at both ensemble seeds, into `results/demos/runs/`; an interrupted run resumes | ~8-10 h |
| `build-figures.sh` | builds every figure and table the manuscript uses, into `results/demos/{figures,tables}/` | seconds |
| `check.sh` | the regression suite: the `% GENERATED` headers, the lit-search pipeline's eight checks, the demo tables and figures against a fresh build, and the run outputs against `MANIFEST.sha256` | ~2-3 min |
| `sync-manuscript.sh` | mirrors the prose from the Overleaf clone into `manuscript/`; reports by default, copies with `--apply` | seconds |
| `publish-results.sh` | copies generated figures, tables and numbers into the Overleaf clone; reports by default, copies with `--apply` | seconds |
| `build-docx.sh` | Word copies of the manuscript and supplement for collaborators to comment on, into `results/manuscript-docx/` (not in git); needs pandoc | seconds |

`sync-manuscript.sh` and `publish-results.sh` are two one-way mirrors over disjoint sets of
files, not a bidirectional sync; see "Keeping the manuscript in step" in the top-level
`README.md`.

Not yet written: `build.sh`, the whole chain from analysis to a compiled PDF, plus the
flatten-to-one-file step Springer Nature's submission format wants.

The correlated-OU sensitivity runs for Demo 2 are deliberately not in `run-demos.sh`: they
are exploratory, and `analysis/notebooks/demo-covid/03-correlated-ou.ipynb` has their
commands.
