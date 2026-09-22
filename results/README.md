# results

Generated outputs only. Nothing here should be hand-edited; everything should be reproducible
by rerunning the code that made it.

`lit-search/` holds the software-landscape survey's outputs: the screening shortlists and
set-aside lists, the recall-audit strata, `counts.json` (every number Appendix S1 quotes),
the candidate-register workbook, Table 1 as LaTeX, the PRISMA flow, and
`MANIFEST.sha256`. Regenerate the lot with

    python3 -m manuscript_analysis.lit_search --check

which also checks its numbers back against the manuscript. The directory is always safe to
delete.
