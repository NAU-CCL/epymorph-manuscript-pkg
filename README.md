# epymorph-manuscript-pkg

Reproducibility package for the epymorph manuscript — data, analysis code, and
manuscript source bundled together following FAIR4RS principles (data → code →
manuscript → results, one repo, one git history).

This structure is meant to be generic: any future python-project-plus-manuscript
could reuse this same layout, not just this one.

## Structure

- `data/` — input data (`raw/`, unmodified; `processed/`, cleaned/derived)
- `analysis/` — a self-contained Python sub-project: the reusable `manuscript_analysis`
  package plus driver notebooks
- `manuscript/` — LaTeX source for the manuscript (one file per section, modular
  supplementary materials)
- `results/` — generated outputs only (figures, compiled PDF, auto-generated
  numbers) — always reproducible by rerunning `scripts/build.sh`, never hand-edited
- `scripts/` — automation (`build.sh`, `check.sh`)

Each subdirectory has its own README explaining what belongs there and, where
relevant, which step of the migration plan populates it.

## Status

This repo is being built up in stages from an existing working folder
(`epymorph-manuscript/`, kept separate as private working notes — knowledge base,
scratch work, drafts-in-progress). See each subdirectory's README for what has
arrived so far.

## Building

`scripts/build.sh` will run the analysis, generate figures/results, and compile the
manuscript. Not yet implemented.

## License

This repository carries two licenses, matching its two kinds of content:

- **Code** (`analysis/`): GPL-3.0-only — see `LICENSE`. This matches the epymorph
  package itself (NAU-CCL/Epymorph, GPL-3.0), which the analysis code depends on.
- **Manuscript text and figures** (`manuscript/`, `results/figures/`): CC BY 4.0 —
  see `LICENSE-MANUSCRIPT.md`.

## Citation

See `CITATION.cff`.
