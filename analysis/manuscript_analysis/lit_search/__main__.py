"""
Run the whole software-landscape screen, end to end.

    python3 -m manuscript_analysis.lit_search            screen, audit, register, counts
    python3 -m manuscript_analysis.lit_search --check    additionally check the manuscript

(or run this file directly: `python3 analysis/manuscript_analysis/lit_search/__main__.py`,
which needs no install because each module resolves its own imports.)

Reads `data/` and `decisions/`, writes `results/` (including Table 1 as LaTeX) and the
register workbook. Nothing it writes is hand-maintained, and nothing it reads from
`decisions/` is ever written back, so this is safe to re-run at any time.

The queries behind the raw exports are recorded in `queries-as-executed.md`,
which sits beside them.
"""
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
CHECK = "--check" in sys.argv


def run(script, *args):
    print(f"\n{'=' * 72}\n{script} {' '.join(args)}\n{'=' * 72}")
    result = subprocess.run([sys.executable, str(SRC / script), *args])
    if result.returncode:
        sys.exit(f"\n{script} failed with exit code {result.returncode}")


# report.py runs the screen and the recall audit itself, then writes counts.json.
run("report.py", *(["--check"] if CHECK else []))
run("register.py", *(["--check"] if CHECK else []))
run("validate_decisions.py", *(["--strict"] if CHECK else []))
run("tables.py")
run("table1_tex.py")
run("prisma.py")
# Last, so the manifest covers everything the run produced.
run("manifest.py")

print(f"\n{'=' * 72}\ndone" + (" - all checks passed" if CHECK else ""))
