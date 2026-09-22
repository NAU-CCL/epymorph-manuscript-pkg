"""Fit and forecast one flu model over one season, writing its outputs to disk.

The command line itself lives in `manuscript_analysis.demos.lib.cli`, shared with the other demos.

Examples
--------
    python -m manuscript_analysis.demos.flu.run_season models.multi_strata_flu:empirical
    python -m manuscript_analysis.demos.flu.run_season models.multi_strata_flu:homogeneous --force -n 20
    python -m manuscript_analysis.demos.flu.run_season models.single_strata -s FLU2025
"""


from manuscript_analysis.demos import paths
from manuscript_analysis.demos.lib.cli import run_season_cli

from .seasons import seasons

MODELS_PACKAGE = "manuscript_analysis.demos.flu"
"""Anchors a relative model spec, so `models.single_strata` still names a model."""


def main():
    run_season_cli(
        seasons,
        default_season="FLU2025",
        output_root=lambda seed: paths.runs("flu", seed=seed),
        package=MODELS_PACKAGE,
    )


if __name__ == "__main__":
    main()
