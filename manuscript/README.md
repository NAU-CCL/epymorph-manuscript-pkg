# manuscript

LaTeX source for the manuscript, using the Springer Nature template
(`sn-jnl.cls`) — covers Nature Portfolio journals generically, including
both Nature Methods and Nature Communications. Final journal choice is
still open (nothing so far depends on it).

## Structure

- `main.tex` — the manuscript itself. `\input`s each file in `sections/`
  in order.
- `sections/` — one file per section (introduction, methods, results,
  discussion). All PLACEHOLDER content right now — nothing has been
  migrated from the old working drafts yet.
- `supplementary/` — a separate document (`supplement-main.tex`, its own
  `\documentclass`) for Supplementary Information, `\input`ing one file
  per appendix (S1, S2, ...).
- `references.bib` — empty for now; will be populated via Zotero's
  Better BibTeX auto-export.
- `sn-jnl.cls`, `sn-*.bst` — Springer Nature template support files,
  copied from the Overleaf project so this directory compiles standalone
  (not only inside Overleaf).

## A note on modularity vs. the Springer Nature template

The template's own `sn-article.tex` says: "Please do not use \input{...}
to include other tex files. Submit your LaTeX manuscript as one .tex
document." This is a SUBMISSION-FORMAT requirement from Springer
Nature/Nature Portfolio's production system, not a technical limitation —
`\input` compiles fine here and on Overleaf. We draft modularly anyway
(one file per section, far easier to review and diff in git) and will
FLATTEN everything into a single file at submission time via
`scripts/build.sh` (not yet written). Likewise, Nature Portfolio's eJP
submission system wants references pasted directly into the manuscript
file rather than a `\bibliography{}` call — also handled by the flatten
step, not by changing how we draft.

## Syncing with Overleaf

This directory is the reproducibility source of truth. A copy of it
(minus this README) lives in the separate `epymorph_ms_overleaf/`
repo/clone, which Overleaf's GitHub sync keeps in sync with the live
editor. See the migration plan (project memory) for the full sync
workflow and the credential constraint on who runs `git push`/`pull`.
