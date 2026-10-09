"""Rebuild what can be rebuilt in minutes, and compare it with what is committed: `just check`.

A file that stopped agreeing with the code that produces it is named rather than quietly
shipped. Run it before and after every change. Exits non-zero on the first failure.

The demos are checked only if their runs are on disk (git does not carry them; see
`results/demos/README.md`). Their figures and tables are rebuilt into a scratch folder,
never over the committed ones: matplotlib's drawing carries last-bit floating-point noise
from one process to the next, so a figure is compared by its pixels, and rebuilding it in
place would show as a change in git when nothing changed.
"""

import os
import sys
import tempfile
from pathlib import Path

from manuscript_analysis import util
from manuscript_analysis.__main__ import (
    DEMOS,
    ROOT,
    ProjectPaths,
    results_checksums,
    run_demo,
    run_lit_search,
)

os.environ["PYTHONHASHSEED"] = "0"  # as in the build; see run_demo
sys.stdout.reconfigure(line_buffering=True)  # keep each line in order with the rebuilds' own
paths = ProjectPaths.from_root(ROOT)


def fail(heading: str, problems: list[str]) -> None:
    print(f"\nFAILED: {heading}", *problems, sep="\n    ")
    sys.exit(1)


# 1. Every .tex under results/ is written by code and says so on its first line. Checked
#    before anything is rebuilt, so a hand edit that removed the header is caught rather
#    than silently overwritten.
unmarked = []
for path in sorted(paths.results.rglob("*.tex")):
    if not path.read_text().startswith("% GENERATED"):
        unmarked.append(str(path.relative_to(ROOT)))
if unmarked:
    fail("no % GENERATED header (hand-written, or hand-edited?)", unmarked)
print("Every .tex under results/ carries its % GENERATED header")

# 2. The software-landscape search, rebuilt in place, with its own eight checks. Its
#    outputs are byte-stable, so this leaves git clean unless something really changed.
run_lit_search(check=True)

# 3. results/ against checksums.sha256: the search's outputs just rebuilt, and the demos'
#    figures and tables as committed.
problems = util.compare_checksums(
    util.read_checksums(paths.results / "checksums.sha256"), results_checksums(paths)
)
if problems:
    fail("results/ differs from results/checksums.sha256", problems)
print("results/ matches results/checksums.sha256")

# 4. The demos, if their runs are here.
if not paths.runs.exists():
    print("\nresults/demos/runs/ absent: skipping the demo checks. Run `just build` to fit "
          "the runs (hours), or fetch the archive; see results/demos/README.md.")
    print("\nall checks passed")
    sys.exit(0)

problems = util.compare_checksums(
    util.read_checksums(paths.results / "demos" / "runs.sha256"),
    util.checksums(paths.runs, exclude={"run.json"}),
)
if problems:
    fail("the runs differ from results/demos/runs.sha256 (expected on a different "
         "platform; there, compare the tables)", problems)
print("The runs match results/demos/runs.sha256")

for name in DEMOS:
    with tempfile.TemporaryDirectory() as scratch:
        # Stops, rather than fitting for hours, if a run is missing.
        run_demo(paths, name, output_dir=Path(scratch), fit_missing_runs=False)
        problems = util.drifted(Path(scratch), paths.results / "demos")
    if problems:
        fail(f"{name}.ipynb no longer reproduces results/demos/", problems)
    print(f"{name}.ipynb reproduces its figures and tables")

print("\nall checks passed")
