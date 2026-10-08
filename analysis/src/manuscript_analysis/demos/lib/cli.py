"""The shared `run_season` command line, used by every demo.

Following `../FluSight-pipeline/run_season.py`, a model is named by its import path and
the season is named separately. Everything here is demo-agnostic: the model says which
observations it wants (`ForecastModel.observations_source`) and which nodes it runs on
(its own RUME's scope), and the season says how long the experiment is. A demo's
`run_season.py` is then a few lines.
"""

import importlib
import json
import time
from argparse import ArgumentParser
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol

from manuscript_analysis.demos.lib.forecasting import (
    ForecastModel,
    run_rolling_origin,
    write_outputs,
)
from manuscript_analysis.scoring import HUB_QUANTILE_LEVELS

__all__ = ["load_model", "run_season_cli"]

DEFAULT_REALIZATIONS = 300
"""Raised from 100 on 2026-09-16.

At 100 the per-jurisdiction comparison was not reproducible: seed-to-seed correlation of
the per-state WIS ratio was near zero, and 18 of 51 jurisdictions changed which model they
favoured. At 300 the seeds agree on 43 of 51, the median absolute difference between them
falls 3.5x, and an apparent horizon-0 penalty turned out to be an ensemble artifact. The
cheap setting is now the one you have to ask for. See `demo-flu/sensitivity/README.md`.
"""


class SeasonLike(Protocol):
    """What the runner needs of a season; see a demo's `seasons.py`."""

    name: str
    disease: str
    start_date: Any
    weeks: int
    burn_in_weeks: int
    horizon_weeks: int


def load_model(spec: str, package: str | None = None) -> ForecastModel:
    """Resolve `package.module` or `package.module:attribute` to a `ForecastModel`.

    The bare form takes `model`, as FluSight does. The `:attribute` form lets one
    module hold several named models, which the mixing and movement modules do.

    `package` anchors a relative spec, so a demo's own models can still be named the
    short way (`models.single_strata`) rather than by their full dotted path. A spec
    that is already absolute, or that starts with a dot, is used as written.
    """
    module_name, _, attribute = spec.partition(":")
    if package is not None and not module_name.startswith("."):
        module_name = f".{module_name}"
    module = importlib.import_module(module_name, package=package)
    model = getattr(module, attribute or "model", None)
    if not isinstance(model, ForecastModel):
        available = sorted(
            name
            for name, value in vars(module).items()
            if isinstance(value, ForecastModel)
        )
        raise SystemExit(
            f"{spec!r} is not a ForecastModel; "
            f"{module_name} offers: {', '.join(available) or '(none)'}"
        )
    return model


def run_season_cli(
    seasons: Mapping[str, SeasonLike],
    default_season: str,
    output_root: Path | Callable[[int], Path],
    argv: list[str] | None = None,
    package: str | None = None,
) -> None:
    """Parse arguments, run one model over one season, write its outputs.

    `output_root` may be a callable taking the ensemble seed, for an output tree that
    keeps each seed's runs apart. That is what both demos pass: a replicate is then a
    `--seed` away rather than a hand-chosen `--output_folder`, which is how the two
    demos came to organise their seed-1 runs differently in the first place.

    `package` anchors relative model specs; see `load_model`.
    """
    parser = ArgumentParser(description="Run one model over one season.")
    parser.add_argument(
        "model_module",
        help="Import path of the model, e.g. models.multi_strata_flu:empirical",
    )
    parser.add_argument("-o", "--output_folder", default=None,
                        help="Defaults to <output_root>/<model name>.")
    parser.add_argument("-s", "--season", default=default_season,
                        choices=sorted(seasons))
    parser.add_argument("-n", "--num_realizations", type=int,
                        default=DEFAULT_REALIZATIONS)
    parser.add_argument("-b", "--burn_in_weeks", type=int, default=None,
                        help="Weeks assimilated before the first forecast. "
                             "Defaults to the season's own value.")
    parser.add_argument("-z", "--horizon_weeks", type=int, default=None,
                        help="Defaults to the season's own value.")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--force", action="store_true",
                        help="Re-run even if the output folder is already populated.")
    args = parser.parse_args(argv)

    season = seasons[args.season]
    model = load_model(args.model_module, package=package)
    if model.disease != season.disease:
        raise SystemExit(
            f"{model.name} is a {model.disease} model; "
            f"{season.name} is {season.disease}"
        )
    burn_in_weeks = args.burn_in_weeks or season.burn_in_weeks
    horizon_weeks = args.horizon_weeks or season.horizon_weeks

    # Check for an existing run before anything else: there is nothing to validate
    # about a model we are not going to run.
    root = output_root(args.seed) if callable(output_root) else Path(output_root)
    output_folder = Path(args.output_folder or root / model.name)
    # The season's NAME is not enough: its window can be redefined under the same name.
    requested = {
        "season": season.name,
        "season_start": str(season.start_date),
        "season_weeks": season.weeks,
        "num_realizations": args.num_realizations,
        "burn_in_weeks": burn_in_weeks,
        "horizon_weeks": horizon_weeks,
        "seed": args.seed,
    }
    existing = output_folder / "run.json"
    if existing.exists() and not args.force:
        stored = json.loads(existing.read_text())
        changed = {
            k: (stored.get(k), v) for k, v in requested.items() if stored.get(k) != v
        }
        if not changed:
            print(f"{output_folder} is already populated; pass --force to re-run.")
            return
        # Skipping here would quietly score a run that answers a different question.
        print(f"{output_folder} holds a run with different settings, re-running:")
        for key, (was, now) in changed.items():
            print(f"    {key}: {was} -> {now}")

    if model.observations_source is None:
        raise SystemExit(f"{model.name} has no observations_source")

    source = model.observations_source()
    locations = list(model.rume.scope.node_ids)

    print(f"{model.name}: {season.name}, {len(locations)} locations, "
          f"{season.weeks} weeks, {args.num_realizations} realizations")
    started = time.monotonic()
    result = run_rolling_origin(
        model,
        source,
        start_date=season.start_date,
        num_weeks=season.weeks,
        burn_in_weeks=burn_in_weeks,
        horizon_weeks=horizon_weeks,
        num_realizations=args.num_realizations,
        quantile_levels=HUB_QUANTILE_LEVELS,
        seed=args.seed,
    )
    elapsed = time.monotonic() - started

    write_outputs(
        result,
        model,
        output_folder,
        locations=locations,
        run_info={
            **requested,
            "elapsed_seconds": round(elapsed, 1),
        },
    )
    print(f"  {len(result.reference_dates)} origins in {elapsed / 60:.1f} min "
          f"-> {output_folder}")
