"""Fit and forecast one COVID model over one season, writing its outputs to disk.

The command line itself lives in `manuscript_analysis.demos.lib.cli`, shared with the other demos, so this is
the same ten lines as `demo-flu/run_season.py`.

Examples
--------
    python -m manuscript_analysis.demos.covid.run_season models.spatial_movement:movement
    python -m manuscript_analysis.demos.covid.run_season models.spatial_movement:county
    python -m manuscript_analysis.demos.covid.run_season models.state_aggregate:model --force -n 20
"""


from manuscript_analysis.demos import paths
from manuscript_analysis.demos.lib.cli import run_season_cli

from .seasons import seasons

MODELS_PACKAGE = "manuscript_analysis.demos.covid"
"""Anchors a relative model spec, so `models.single_strata` still names a model."""


def main():
    run_season_cli(
        seasons,
        default_season="COVID2020",
        output_root=lambda seed: paths.runs("covid", seed=seed),
        package=MODELS_PACKAGE,
    )


if __name__ == "__main__":
    main()
