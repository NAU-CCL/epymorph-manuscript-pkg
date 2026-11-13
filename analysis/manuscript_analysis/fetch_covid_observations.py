"""How Demo 2's frozen observations were made.

This is intended as a one-time operation, where the data are cached for future use.
It is not repeated during a normal build.

    uv run --project analysis python -m manuscript_analysis.fetch_covid_observations <output.csv>

Fetches both CDC series for the 32 counties over the 2020-21 season, imputes the suppressed
death counts, and writes the tidy CSV to `data/demos/covid/observations.csv` (or the given path).

The sources are no longer revised and the imputation has a fixed seed, so on 2026-10-08
a fresh fetch reproduced the frozen file byte for byte. The script requires network access,
the CDC series need no key, and the county populations are read from their frozen copy in `data/raw/`.
"""

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from epymorph.adrio import cdc
from epymorph.adrio.acs5 import Population
from epymorph.geography.us_census import CountyScope
from epymorph.time import TimeFrame
from scipy.stats import poisson

from manuscript_analysis.data import ProvenanceCachedADRIO

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_PATH = ROOT / "data" / "demos" / "covid" / "observations.csv"

STATES = ["MA", "CT", "NH"]
CENSUS_YEAR = 2015  # the county geography the models run on
CDC_YEAR = 2019  # the county vintage the CDC datasets are keyed on
SEASON = TimeFrame.of(start_date=date(2020, 8, 9), duration_days=7 * 35)

SUPPRESSED_LO, SUPPRESSED_HI = 1, 9  # CDC suppresses a weekly count in this range
FILL_SEED = 0  # the imputation is a random draw, made once with this seed


def impute_suppressed(lam: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Draw from Poisson(lam) truncated to the censoring interval {LO, ..., HI}."""
    k = np.arange(SUPPRESSED_LO, SUPPRESSED_HI + 1)
    weights = poisson.pmf(k[:, None], np.maximum(lam.ravel(), 1e-9)[None, :])
    totals = weights.sum(axis=0, keepdims=True)
    degenerate = (totals <= 0).ravel()
    weights = np.where(totals > 0, weights / np.maximum(totals, 1e-300), 0.0)
    draw = (rng.random(weights.shape[1])[None, :] > np.cumsum(weights, axis=0)).sum(axis=0)
    out = k[np.clip(draw, 0, len(k) - 1)]
    out[degenerate] = SUPPRESSED_HI
    return out.reshape(lam.shape)


def main(path: Path | None = None) -> None:
    if path is None:
        path = DEFAULT_OUT_PATH
    if path.exists():
        sys.exit(f"{path} exists; write to a new file and compare it with the frozen one")

    scope = CountyScope.in_states(STATES, year=CENSUS_YEAR)
    cdc_scope = CountyScope.in_states(STATES, year=CDC_YEAR)
    if list(cdc_scope.node_ids) != list(scope.node_ids):
        sys.exit(f"the county sets differ between {CENSUS_YEAR} and {CDC_YEAR}")
    context = {"scope": cdc_scope, "time_frame": SEASON}

    deaths_raw = (
        cdc.CountyDeaths(cause_of_death="COVID-19", fix_redacted=False, fix_missing=False)
        .with_context(**context).inspect().result
    )
    death_dates = np.ma.getdata(deaths_raw["date"])[:, 0]
    suppressed = np.ma.getmaskarray(deaths_raw["value"])
    observed = np.ma.getdata(deaths_raw["value"]).astype(np.float64)

    census_raw = (
        cdc.COVIDFacilityHospitalization(age_group="both", fix_redacted=2, fix_missing=False)
        .with_context(**context).inspect().result
    )
    if np.ma.getmaskarray(census_raw["value"]).any():
        sys.exit("the hospital census is masked; the filter cannot take a masked source")
    census = np.ma.getdata(census_raw["value"]).astype(np.float64) / 7.0
    census_dates = np.ma.getdata(census_raw["date"])[:, 0]

    offset = (death_dates[0] - census_dates[0]).astype(int)
    if offset != 6:
        sys.exit(f"the two series are {offset} days apart, not 6: not the same MMWR weeks")

    # Impute the suppressed cells from the region's own per-capita mortality that week.
    population = (
        ProvenanceCachedADRIO(
            Population(),
            cache_path=ROOT / "data" / "raw" / "covid-population-counties-2015-ma-ct-nh.npz",
            description="ACS 5-year population per county; 2015 vintage; MA, CT, NH",
        )
        .with_context(scope=scope, time_frame=SEASON)
        .inspect().result.astype(np.int64)
    )
    weekly_regional = np.where(suppressed, 0, observed).sum(axis=1)
    pop_reporting = np.array(
        [population[~suppressed[t]].sum() for t in range(len(death_dates))], dtype=np.float64
    )
    lam = (weekly_regional / pop_reporting)[:, None] * population[None, :]
    filled = impute_suppressed(lam, np.random.default_rng(FILL_SEED))
    deaths = np.where(suppressed, filled, observed).astype(np.float64)

    frames = []
    for name, values, dates in (
        ("census", census, census_dates),
        ("deaths", deaths, death_dates),
    ):
        for node, location in enumerate(scope.node_ids):
            frames.append(pd.DataFrame({
                "date": dates,
                "location": location,
                "quantity": name,
                "value": values[:, node],
                "suppressed": suppressed[:, node] if name == "deaths" else False,
            }))
    table = pd.concat(frames, ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    table.sort_values(["quantity", "date", "location"]).to_csv(path, index=False)
    print(f"wrote {path}")


if __name__ == "__main__":
    if "--help" in sys.argv:
        sys.exit(__doc__)
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    main(out)
