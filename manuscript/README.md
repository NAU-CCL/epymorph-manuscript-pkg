# manuscript

LaTeX source for the manuscript, using the Springer Nature template
(`sn-jnl.cls`) — covers Nature Portfolio journals generically, including
both Nature Methods and Nature Communications. Final journal choice is
still open (nothing so far depends on it).

## Structure

- `main.tex` — the manuscript itself. `\input`s each file in `sections/`
  in order.
- `sections/` — one file per section (introduction, methods, results,
  discussion). Introduction and Methods were ported from `drafts/intro-v05.md`
  and `drafts/methods_v05.md` (in the maintainer's working folder) on
  2026-09-21; Results and Discussion are still PLACEHOLDER. The `.tex` files
  are now the working copy, and the markdown drafts are frozen.
- `supplementary/` — a separate document (`supplement-main.tex`, its own
  `\documentclass`) for Supplementary Information, `\input`ing one file
  per appendix (S1, S2, ...). Compile it from inside `supplementary/` (its
  `\bibliography` and `\input` paths assume that working directory).
- `references.bib` — copy of `lit/epymorph-2026.bib` (a Zotero export, in the
  maintainer's working folder) with three small patches: `file = {...}` lines removed, `mckinney_data_2010` recast
  as `@article` (sn-nature.bst crashes on `@inproceedings` without an editor),
  and `v_individual-level_2020` author fixed. It also has one commented stub,
  `ning_iterated_2023`, that is not in Zotero yet.
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

The prose is edited in Overleaf, which round-trips with the separate
`epymorph_ms_overleaf` repository. This directory is a one-way mirror of
it, refreshed by `scripts/sync-manuscript.sh`; edit in Overleaf, not here,
or the next `--apply` discards the edit. Generated figures, tables and
numbers go the other way, via `scripts/publish-results.sh`. The two
scripts cover disjoint sets of files; see "Keeping the manuscript in
step" in the top-level `README.md`.
