"""Build every result the manuscript uses: `python -m manuscript_analysis`, or `just build`.

Minutes with the runs on disk; about five hours on a fresh clone, which fits them.
`results/demos/README.md` says how to fetch the archived runs instead.
"""

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

import papermill

from manuscript_analysis import lit_search, util

ROOT = Path(__file__).resolve().parents[2]

DEMOS = {"demo-flu": "flu", "demo-covid": "covid"}
"""Each case study's notebook, and the name its runs are filed under."""

CHECKSUMMED = ["lit-search", "demos/figures", "demos/tables"]
"""What `results/checksums.sha256` covers, relative to `results/`: everything the build
writes, except the runs (which have their own file) and the executed notebooks (which
record how long each cell took)."""


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    data: Path
    results: Path
    runs: Path
    notebooks: Path

    @staticmethod
    def from_root(root: Path, runs: Path | None = None) -> "ProjectPaths":
        return ProjectPaths(
            root=root,
            data=root / "data",
            results=root / "results",
            runs=runs if runs is not None else root / "results" / "demos" / "runs",
            notebooks=root / "analysis" / "manuscript_analysis",
        )


def main() -> None:
    description = None if __doc__ is None else __doc__.splitlines()[0]
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--runs-dir", type=Path, default=None,
        help="where the runs are read from, and fitted into if missing "
        "(default: results/demos/runs)",
    )
    args = parser.parse_args()
    paths = ProjectPaths.from_root(ROOT, runs=args.runs_dir)

    # 1. The software-landscape search: Table 1, Appendix S1 and its flow figure.
    lit_search.run()

    # 2. The two case studies. Each is one notebook, read top to bottom. A run already on
    #    disk is reused; a missing one is fitted, which takes hours.
    for name in DEMOS:
        run_demo(paths, name, output_dir=paths.results / "demos")

    # 3. Checksums: of what the build wrote, and separately of the runs.
    write_checksums(paths)
    compare_runs(paths)


def run_demo(
    paths: ProjectPaths, name: str, output_dir: Path, fit_missing_runs: bool = True
) -> None:
    print(f"Running {name}.ipynb", flush=True)
    # The PDFs embed a subset of each font, and matplotlib orders its glyphs by Python's
    # string hashing, which is randomised per process unless pinned. The notebook's kernel
    # is a new process, so it inherits this.
    os.environ["PYTHONHASHSEED"] = "0"
    papermill.execute_notebook(
        input_path=paths.notebooks / f"{name}.ipynb",
        # The executed copy, figures and all, is the readable record of the analysis.
        output_path=output_dir / f"{name}.ipynb",
        parameters={
            "data_dir": str(paths.data),
            "runs_dir": str(paths.runs / DEMOS[name]),
            "output_dir": str(output_dir),
            "fit_missing_runs": fit_missing_runs,
        },
        cwd=paths.notebooks,
    )


def results_checksums(paths: ProjectPaths) -> dict[str, str]:
    found = {}
    for folder in CHECKSUMMED:
        for name, digest in util.checksums(paths.results / folder).items():
            found[f"{folder}/{name}"] = digest
    return found


def write_checksums(paths: ProjectPaths) -> None:
    found = results_checksums(paths)
    util.write_checksums(paths.results / "checksums.sha256", found)
    print(f"Wrote results/checksums.sha256: {len(found)} files")


def compare_runs(paths: ProjectPaths) -> None:
    """Hold the runs to `results/demos/runs.sha256`, writing it only if there is none.

    It is never overwritten, so a run that came out differently cannot quietly become the
    new reference. After a deliberate change to the runs, delete it and build again.
    """
    recorded = paths.results / "demos" / "runs.sha256"
    found = util.checksums(paths.runs, exclude={"run.json"})  # run.json records elapsed time
    if not recorded.exists():
        util.write_checksums(recorded, found)
        print(f"Wrote results/demos/runs.sha256: {len(found)} files")
        return
    problems = util.compare_checksums(util.read_checksums(recorded), found)
    if problems:
        print("The runs differ from results/demos/runs.sha256 (expected on a different "
              "platform; compare results/demos/tables/ instead):", *problems, sep="\n    ")
    else:
        print(f"The runs match results/demos/runs.sha256: {len(found)} files")


if __name__ == "__main__":
    main()
