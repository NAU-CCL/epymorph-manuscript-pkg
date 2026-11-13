# scripts

Automation for the pipeline, run from the repository root, mostly through the `justfile`
(`just check`, `just publish`, ...). The build itself is `python -m manuscript_analysis`
(`just build`). Each script's header comment has the detail; the top-level `README.md`
has the workflow they fit into.

| script | what it does | cost |
|---|---|---|
| `check.py` (`just check`) | the regression suite: the `% GENERATED` headers, the lit-search pipeline's eight checks, `results/` against `checksums.sha256`, the runs against `results/demos/runs.sha256`, and both demo notebooks rerun into a scratch folder (tables byte for byte, figures pixel for pixel) | ~4 min |
| `sync-manuscript.sh` (`just sync-manuscript`) | mirrors the prose from the Overleaf clone into `manuscript/`; reports by default, copies with `--apply` | seconds |
| `publish-results.sh` (`just publish`) | copies generated figures, tables and numbers into the Overleaf clone; reports by default, copies with `--apply` | seconds |
| `build-docx.sh` (`just docx`), with `build_docx.py` | Word copies of the manuscript and supplement for collaborators to comment on, into `results/manuscript-docx/` (not in git); needs pandoc | seconds |

`sync-manuscript.sh` and `publish-results.sh` are two one-way mirrors over disjoint sets of
files, not a bidirectional sync; see "Keeping the manuscript in step" in the top-level
`README.md`.

Not yet written: a recipe for the compiled PDF, plus the flatten-to-one-file step Springer
Nature's submission format wants (see "Still to come" in the top-level `README.md`).
