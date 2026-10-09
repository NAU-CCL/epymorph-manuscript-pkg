"""The software-landscape search behind Appendix S1, Table 1 and the candidate register.

`run()` is the whole pipeline, in order; `just build` calls it, and `just check` calls it
with `check=True`. Reads `data/lit-search/`, writes `results/lit-search/`. Nothing it writes
is hand-maintained, and nothing it reads from `decisions/` is ever written back, so it is
safe to re-run at any time. See README.md.
"""
from . import manifest, prisma, register, report, table1_tex, tables, validate_decisions


def run(check=False):
    """Screen, audit, count, then everything built from the counts and the decisions.

    With `check`, also check the numbers and term list against the manuscript, and fail
    rather than warn on any problem in the decisions or the register.
    """
    steps = [
        # Runs the screen and the recall audit itself, then writes counts.json.
        ("report", lambda: report.main(check=check)),
        ("register", lambda: register.main(check=check)),
        ("validate_decisions", lambda: validate_decisions.main(strict=check)),
        ("tables", tables.main),
        ("table1_tex", table1_tex.main),
        ("prisma", prisma.main),
        ("manifest", manifest.main),
    ]
    for name, step in steps:
        print(f"\n{'=' * 72}\n{name}\n{'=' * 72}", flush=True)
        step()
    print(f"\n{'=' * 72}\ndone" + (" - all checks passed" if check else ""))
