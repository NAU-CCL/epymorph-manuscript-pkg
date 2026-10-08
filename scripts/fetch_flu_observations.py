"""How Demo 1's frozen observations were made. No build runs this.

    cd analysis
    uv run python ../scripts/fetch_flu_observations.py <output.csv>

Fetches CDC's weekly influenza admissions by age group, and CDC's own all-ages total, for
every state, DC and Puerto Rico over the 2025-26 season, and writes the tidy CSV that
`data/demos/flu/observations.csv` is a frozen copy of. CDC revises these series every
week, so a fetch today will not reproduce the frozen file; that is why it is frozen.
Never point this at the frozen file: it refuses to overwrite an existing one.

Moved out of `flu_season.py` in restructure step 6 (2026-10-08), unchanged in substance.
Needs network access; the CDC series need no key.
"""

import sys
from datetime import date
from pathlib import Path

import pandas as pd
from epymorph.adrio.cdc import CurrentStateAdmissions
from epymorph.geography.us_census import StateScope
from epymorph.time import TimeFrame

STATES = [
    "AK", "AL", "AR", "AZ", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "HI", "IA",
    "ID", "IL", "IN", "KS", "KY", "LA", "MA", "MD", "ME", "MI", "MN", "MO", "MS",
    "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH", "OK", "OR", "PA",
    "PR", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY",
]
SEASON = TimeFrame.of(start_date=date(2025, 9, 13), duration_days=7 * 38)

# (the name the observations use, CDC's name for the age group)
GROUPS = [
    ("age_00-04", "0 to 4"),
    ("age_05-17", "5 to 17"),
    ("age_18-49", "18 to 49"),
    ("age_50-64", "50 to 64"),
    ("age_65-74", "65 to 74"),
    ("age_75-99", "75 and above"),
    # CDC's all-ages total, about 0.25% above the sum of the groups. Kept for checking;
    # every model is fitted and scored on the sum of the groups instead.
    ("total_reported", "Total"),
]


def main(path: Path) -> None:
    if path.exists():
        sys.exit(f"{path} exists; write to a new file and compare it with the frozen one")
    scope = StateScope.in_states(STATES, year=2024)
    frames = []
    for name, group in GROUPS:
        result = (
            CurrentStateAdmissions(disease="Influenza", age_group=group)
            .with_context(scope=scope, time_frame=SEASON)
            .inspect().result
        )
        for node, location in enumerate(scope.node_ids):
            frames.append(pd.DataFrame({
                "date": result["date"][:, node],
                "location": location,
                "quantity": name,
                "value": result["value"][:, node],
            }))
    table = pd.concat(frames, ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    table.sort_values(["date", "location", "quantity"]).to_csv(path, index=False)
    print(f"wrote {path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
