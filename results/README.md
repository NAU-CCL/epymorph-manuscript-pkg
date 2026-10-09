# results

Generated outputs only, written by `just build`. Nothing here should be hand-edited;
everything can be reproduced by rerunning the code that made it.

`lit-search/` holds the software-landscape survey's outputs: the screening shortlists and
set-aside lists, the recall-audit strata, `counts.json` (every number Appendix S1 quotes),
the candidate-register workbook, Table 1 as LaTeX, the PRISMA flow, and `MANIFEST.sha256`
(the checksums of the archived search exports; the pipeline fails if any of them
changes). Always safe to delete.

`demos/` holds the two case studies' outputs: the manuscript's figures and tables, which
are in git, and the runs they are computed from, which are not (~1 GB, about five hours to
rebuild). See `demos/README.md` before deleting anything there.

`checksums.sha256` is the SHA-256 of everything in `lit-search/`, `demos/figures/` and
`demos/tables/`, rewritten by every build; `just check` holds the committed files to it.
The runs have their own, `demos/runs.sha256`.
