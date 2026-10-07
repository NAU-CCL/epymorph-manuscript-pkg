"""Generate the demos' score tables, as CSV to read and as LaTeX for the supplement.

The counterpart to `export_manuscript.py`: that file composes the figures, this one emits
the numbers beside them. Both are driven by the same `load()` the notebooks call, so the
supplement, the notebook and the paper cannot disagree.

Follows the pattern `results/lit-search/table-1-maintext.tex` already sets in the package
repo: the `.tex` is a **projection** of the pipeline's own output, carries a header saying
so, and is **never hand-edited**. `--check` regenerates every table and fails if what is on
disk differs, which is what makes "never hand-edit" enforceable rather than a request.

Six tables, in the order the supplement wants them:

| file | what it is |
|---|---|
| `flu-skill` | WIS and log WIS with their relative forms, per-horizon log WIS, coverage |
| `flu-reproducibility` | median ratio, wins and sign test at both seeds |
| `flu-by-jurisdiction` | all 51 scored jurisdictions; a reference table, see its caption |
| `covid-skill` | WIS and log WIS with their relative forms, one row per model per quantity |
| `covid-reproducibility` | relative log WIS at both seeds and their geometric mean |
| `covid-by-state` | the three scored states, both quantities, with the movement contrast |

**Scales.** The manuscript's headline scale is log WIS, as in CDC's FluSight evaluations
(`scoring.HEADLINE_SCALE`). The two skill tables report the natural scale beside it; every
other table, like every figure, is on the log scale only. Relative WIS is always the ratio
of geometric means (`scoring.relative_wis`).

Usage:

    python -m manuscript_analysis.demos.tables                 # write everything to tables/
    python -m manuscript_analysis.demos.tables --check         # fail if what is on disk has drifted
    python -m manuscript_analysis.demos.tables --tables-dir DIR
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from manuscript_analysis.demos import paths
from manuscript_analysis.demos.covid import evaluation as covid
from manuscript_analysis.demos.flu import evaluation as flu
from manuscript_analysis.demos.lib.figures import use_manuscript_style
from manuscript_analysis.demos.lib.scoring import SCORE_LABELS

HERE = Path(__file__).resolve().parent

OUTPUT_DIR = paths.TABLES
"""Where the tables land. The one thing to repoint when the demos move into
`epymorph-manuscript-pkg`, exactly as `export_manuscript.OUTPUT_DIR` is."""

GENERATED_BY = "manuscript_analysis.demos.tables"


# --- LaTeX ------------------------------------------------------------------------


_ESCAPES = {
    "\\": "\\textbackslash{}", "&": "\\&", "%": "\\%", "$": "\\$", "#": "\\#",
    "_": "\\_", "{": "\\{", "}": "\\}", "~": "\\textasciitilde{}",
    "^": "\\textasciicircum{}",
}


DECIMALS = 3
"""Decimal places for every number in a table.

Fixed rather than per-column: `round()` alone prints 1.0 beside 0.335, which reads as
different precision when it is the same number of digits."""


def _format(value) -> str:
    """One cell as text. Floats get a fixed number of decimals, everything else str()."""
    if value is None:
        return ""
    if isinstance(value, float):
        return "" if np.isnan(value) else f"{value:.{DECIMALS}f}"
    if isinstance(value, np.floating):
        return f"{float(value):.{DECIMALS}f}"
    return str(value)


def _escape(value) -> str:
    """LaTeX-escape a cell. Written out rather than imported: the whole dependency on
    `DataFrame.to_latex` is jinja2, and a booktabs tabular is fifteen lines."""
    return "".join(_ESCAPES.get(character, character) for character in _format(value))


# A value-column header longer than this breaks onto two lines, so that a table of short
# numbers is not as wide as its longest header. Every main-text header is shorter.
HEADER_WRAP = 12


def _header_cell(text: str) -> str:
    """A bold value-column header, on two right-aligned lines if it is long."""
    words = text.split(" ")
    if len(text) <= HEADER_WRAP or len(words) == 1:
        return f"\\textbf{{{_escape(text)}}}"

    # Break at the space that leaves the two lines most nearly equal in length.
    best_split = 1
    best_width = len(text)
    for split in range(1, len(words)):
        first = " ".join(words[:split])
        second = " ".join(words[split:])
        width = max(len(first), len(second))
        if width < best_width:
            best_split, best_width = split, width
    first = _escape(" ".join(words[:best_split]))
    second = _escape(" ".join(words[best_split:]))
    return (
        f"\\begin{{tabular}}[b]{{@{{}}r@{{}}}}"
        f"\\textbf{{{first}}} \\\\ \\textbf{{{second}}}"
        f"\\end{{tabular}}"
    )


def _parts(frame: pd.DataFrame) -> tuple[str, str, list[str]]:
    """The pieces of a booktabs table: column alignment, header row, and body rows.

    Index columns are left-aligned and value columns right-aligned.
    """
    index_names = list(frame.index.names)
    if isinstance(frame.index, pd.MultiIndex):
        index_rows = [list(key) for key in frame.index]
    else:
        index_rows = [[key] for key in frame.index]
    index_names = [name or "" for name in index_names]

    alignment = "@{}" + "l" * len(index_names) + "r" * len(frame.columns) + "@{}"
    header = [_escape(name) for name in index_names]
    header += [_header_cell(column) for column in frame.columns]
    header_row = " & ".join(header) + " \\\\"

    rows = []
    for keys, (_, row) in zip(index_rows, frame.iterrows()):
        cells = [_escape(key) for key in keys]
        cells += [_escape(value) for value in row]
        rows.append(" & ".join(cells) + " \\\\")
    return alignment, header_row, rows


def _tabular(frame: pd.DataFrame) -> str:
    """A booktabs tabular, for a table that fits on one page."""
    alignment, header_row, rows = _parts(frame)
    lines = [
        f"\\begin{{tabular}}{{{alignment}}}",
        "\\toprule",
        header_row,
        "\\midrule",
        *rows,
        "\\bottomrule",
        "\\end{tabular}",
    ]
    return "\n".join(lines)


# Tables too tall for one page. They are written as a `longtable`, which breaks across
# pages and repeats its header, instead of a float that LaTeX would push to the end of
# the document. Only the supplement includes them, and it loads the longtable package.
LONG_TABLES = {"tab:flu-by-jurisdiction"}

# Tables whose eight columns are still wider than the supplement's text at \footnotesize,
# even with wrapped headers. They are set one size smaller instead.
COMPACT_TABLES = {"tab:covid-by-state"}


def _longtable(frame: pd.DataFrame, caption: str, label: str, note: str | None) -> str:
    """A booktabs longtable, with the note set after it rather than inside a float."""
    alignment, header_row, rows = _parts(frame)
    lines = [
        "\\begingroup",
        "\\footnotesize",
        "\\setlength{\\tabcolsep}{5pt}",
        "\\setlength{\\LTcapwidth}{\\linewidth}",
        f"\\begin{{longtable}}{{{alignment}}}",
        f"\\caption{{{caption}}}\\label{{{label}}} \\\\",
        "\\toprule",
        header_row,
        "\\midrule",
        "\\endfirsthead",
        "\\toprule",
        header_row,
        "\\midrule",
        "\\endhead",
        "\\bottomrule",
        "\\endfoot",
        *rows,
        "\\end{longtable}",
    ]
    if note is not None:
        lines.append(f"{{\\raggedright\\scriptsize {note}\\par}}")
    lines.append("\\endgroup")
    return "\n".join(lines)


def _to_latex(
    frame: pd.DataFrame,
    caption: str,
    label: str,
    note: str | None = None,
) -> str:
    """One table, as a complete LaTeX environment ready to `\\input`.

    A full environment rather than a bare `tabular`, matching
    `results/lit-search/table-1-maintext.tex`: the caption is part of what is generated,
    so a number quoted in the caption cannot drift from the table beneath it.
    """
    header = [
        f"% GENERATED by {GENERATED_BY} -- do not hand-edit.",
        "% Regenerate:  python -m manuscript_analysis.demos.tables",
    ]
    if label in LONG_TABLES:
        return "\n".join(header) + "\n" + _longtable(frame, caption, label, note) + "\n"

    body = _tabular(frame)
    lines = [
        *header,
        "\\begin{table}[tb]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        "\\scriptsize" if label in COMPACT_TABLES else "\\footnotesize",
        "\\setlength{\\tabcolsep}{5pt}",
        body.rstrip(),
    ]
    if note is not None:
        lines.append(f"\\par\\medskip\\raggedright\\scriptsize {note}")
    lines.append("\\end{table}")
    return "\n".join(lines) + "\n"


# --- Demo 1 -----------------------------------------------------------------------


def _both_scales(natural: pd.DataFrame, log: pd.DataFrame) -> pd.DataFrame:
    """The natural-scale score and its relative form, then everything on the log scale.

    Coverage is taken from the log table. It does not depend on the scale, and this
    checks that rather than assuming it.
    """
    for column in ("cov95", "cov50"):
        if not np.allclose(natural[column], log[column]):
            raise ValueError(f"{column} differs between scales; it should not")
    return pd.concat([natural[["WIS", "rel WIS"]], log], axis=1)


def flu_skill(ev, natural_ev) -> pd.DataFrame:
    """WIS and log WIS with relative forms, per-horizon log WIS and coverage, by model."""
    log = flu.wis_table(ev)
    first = ["log WIS", "rel log WIS"]
    log = log[first + [column for column in log.columns if column not in first]]
    frame = _both_scales(flu.wis_table(natural_ev), log)
    frame.index = [flu.LABELS[model] for model in frame.index]
    frame.index.name = "model"
    return frame.round(3)


def flu_reproducibility(ev, replicate) -> pd.DataFrame:
    """The headline comparison at both seeds: median ratio, wins, and the sign test.

    These are the numbers the paper quotes, and until now they were **typed by hand**
    into the notebook's section 5 markdown. Generating them is the point of this file.

    The sign test is valid here even though the per-jurisdiction assignment is not
    reproducible: think of it as 51 biased coins, where the count is reproducible and
    which coins land heads is not. Per-jurisdiction noise costs power, not validity.
    """
    rows = []
    for model in flu.MODELS:
        if model == flu.BASELINE:
            continue
        for seed, evaluation in (("0", ev), ("1", replicate)):
            if evaluation is None:
                continue
            ratios = flu.relative_by_unit(evaluation, model)
            wins = int((ratios < 1).sum())
            rows.append({
                "model": flu.LABELS[model],
                "seed": seed,
                "median ratio": round(float(np.median(ratios)), 3),
                "better in": f"{wins} of {len(ratios)}",
                "p": float(binomtest(wins, len(ratios), 0.5).pvalue),
            })
    frame = pd.DataFrame(rows).set_index(["model", "seed"])
    frame["p"] = frame["p"].map(_format_p)
    return frame


def _format_p(value: float) -> str:
    """A p-value as a reader expects it: 0.011, 0.40, or <0.001."""
    if value < 0.001:
        return "<0.001"
    if value < 0.1:
        return f"{value:.3f}"
    return f"{value:.2f}"


# Ratio columns arrive named by model id ("movement / county"); the manuscript names the
# models in words, so the headers do too. Short forms, because a table column is narrow.
FLU_RATIO_LABELS = {
    f"multi-strata-empirical / {flu.BASELINE}": "empirical / unstratified",
    f"multi-strata-homogeneous / {flu.BASELINE}": "homogeneous / unstratified",
}
COVID_RATIO_LABELS = {
    "movement / state": "commuting / state",
    "county / state": "no movement / state",
    "movement / county": "commuting / no movement",
}


def flu_by_jurisdiction(ev) -> pd.DataFrame:
    """Mean WIS per jurisdiction under each model, with ratios against the baseline."""
    frame = flu.wis_by_jurisdiction(
        ev, sort_by=f"multi-strata-empirical / {flu.BASELINE}"
    )
    frame = frame.drop(columns=["fips"])
    headers = []
    for column in frame.columns:
        if column in FLU_RATIO_LABELS:
            headers.append(FLU_RATIO_LABELS[column])
        else:
            headers.append(flu.LABELS.get(column, column))
    frame.columns = headers
    return frame.round(3)


# --- Demo 2 -----------------------------------------------------------------------


def covid_skill(ev, natural_ev) -> pd.DataFrame:
    """WIS and log WIS per model per quantity, with relative forms and coverage."""
    frame = _both_scales(covid.wis_table(natural_ev), covid.wis_table(ev))
    frame.index = pd.MultiIndex.from_tuples(
        [(covid.LABELS[model], covid.AXIS_LABELS[quantity])
         for model, quantity in frame.index],
        names=["model", "quantity"],
    )
    return frame.round(3)


def covid_reproducibility(ev, replicate) -> pd.DataFrame:
    """Relative WIS at both seeds and their geometric mean, per model per quantity.

    The geometric mean rather than the arithmetic one because these are ratios: the
    average of 0.5 and 2.0 should be 1.0, not 1.25.
    """
    label = f"rel {SCORE_LABELS[ev.scale]}"
    rows = []
    for quantity in covid.QUANTITIES:
        for model in covid.MODELS:
            if model == covid.BASELINE:
                continue
            first = covid.relative_pooled(ev, model, quantity)
            row = {
                "model": covid.LABELS[model],
                "quantity": covid.AXIS_LABELS[quantity],
                f"{label}, seed 0": round(first, 3),
            }
            if replicate is not None:
                second = covid.relative_pooled(replicate, model, quantity)
                row[f"{label}, seed 1"] = round(second, 3)
                row["geometric mean"] = round(float(np.sqrt(first * second)), 3)
            rows.append(row)
    return pd.DataFrame(rows).set_index(["model", "quantity"])


def covid_by_state(ev) -> pd.DataFrame:
    """Mean WIS per state per quantity under each model, with ratios."""
    frame = covid.wis_by_location(ev)
    frame = frame.rename(
        columns={model: covid.LABELS[model] for model in covid.MODELS}
    )
    frame = frame.rename(columns=COVID_RATIO_LABELS)
    frame.index = pd.MultiIndex.from_tuples(
        [(place, covid.AXIS_LABELS[quantity]) for place, quantity in frame.index],
        names=["state", "quantity"],
    )
    return frame.round(3)


# --- Driver -----------------------------------------------------------------------

FLU_REPRODUCIBILITY_NOTE = (
    "Both seeds are reported because the aggregate result is reproducible but which "
    "jurisdictions favour each model is not (Table~\\ref{tab:flu-by-jurisdiction})."
)

COVID_REPRODUCIBILITY_NOTE = (
    "Both seeds are reported because the aggregate result is reproducible but which "
    "counties favour each model is not (main-text Fig.~3d)."
)

SCALE_NOTE = (
    r"\emph{log WIS} is scored after transforming observations and forecast quantiles "
    r"by $\log(x+1)$, following CDC's FluSight evaluations in scoring on the log scale; "
    r"the offset is needed because some counts are zero. \emph{rel} columns are "
    r"relative WIS, as FluSight defines it: the geometric mean "
    r"score of each model divided by that of the baseline over the same forecasts, so "
    r"they are not the ratio of the arithmetic means beside them."
)

JURISDICTION_NOTE = (
    "\\textbf{A reference table, not a ranking.} The distribution of the ratio is "
    "reproducible across ensemble seeds but the per-jurisdiction assignment is not, so "
    "the ordering of these rows carries no claim about any individual jurisdiction. "
    "Ratios below~1 favour the stratified model. Scores are log WIS; ratios are relative "
    "log WIS, the ratio of geometric means."
)


CAPTIONS = {
    "flu-skill": (
        r"\textbf{Influenza case study: forecast skill by model.} Weighted interval score pooled over "
        r"25 forecast origins and 51 jurisdictions, on the natural and the log scale, "
        r"with log WIS also shown separately at each horizon (h0--h3, weeks ahead). "
        r"Lower is better. Relative scores are against the unstratified model; "
        r"\emph{cov95} and \emph{cov50} are empirical coverage of the nominal 95\% and "
        r"50\% prediction intervals, which does not depend on the scale."
    ),
    "flu-reproducibility": (
        r"\textbf{Influenza case study: the comparison at two ensemble seeds.} Median of the "
        r"per-jurisdiction relative log WIS against the unstratified model, the number of "
        r"jurisdictions the structured model wins, and a two-sided sign test on that "
        r"count. Both seeds use $R=300$ realizations and are scored against the same "
        r"frozen observations, with every model re-run at each seed."
    ),
    "flu-by-jurisdiction": (
        r"\textbf{Influenza case study: mean log WIS by jurisdiction.} One row per scored "
        r"jurisdiction, sorted by the ratio of the empirical-mixing model to the unstratified "
        r"model."
    ),
    "covid-skill": (
        r"\textbf{COVID-19 case study: forecast skill by model and quantity.} Weighted "
        r"interval score pooled over forecast origins and the three scored states, on the "
        r"natural and the log scale, with coverage as in Table~\ref{tab:flu-skill}. There is "
        r"no pooled "
        r"score across quantities: a hospital census is a stock and deaths are a flow, so "
        r"adding their scores would mean nothing."
    ),
    "covid-reproducibility": (
        r"\textbf{COVID-19 case study: the comparison at two ensemble seeds.} Relative log WIS "
        r"against the "
        r"model with no spatial structure, at each seed and as their geometric mean."
    ),
    "covid-by-state": (
        r"\textbf{COVID-19 case study: mean log WIS by state and quantity.} Ratio columns are "
        r"relative "
        r"log WIS. The final column is the "
        r"informative contrast for the movement question: the same 32 counties with "
        r"commuting on against commuting off, at identical spatial resolution."
    ),
}

NOTES = {
    "flu-skill": SCALE_NOTE,
    "covid-skill": SCALE_NOTE,
    "flu-reproducibility": FLU_REPRODUCIBILITY_NOTE,
    "covid-reproducibility": COVID_REPRODUCIBILITY_NOTE,
    "flu-by-jurisdiction": JURISDICTION_NOTE,
}


def build(
    flu_ev, flu_replicate, covid_ev, covid_replicate, flu_natural, covid_natural
) -> dict:
    """Every table, as `name -> (frame, caption, label, note)`.

    The first four evaluations are on the headline (log) scale; `flu_natural` and
    `covid_natural` are the same seed-0 runs scored on the natural scale, for the two
    skill tables.

    Captions live in `CAPTIONS` rather than inline so that this function reads as the
    list of tables it is, and so a caption can be reworded without touching the code
    that computes the numbers it describes.
    """
    frames = {
        "flu-skill": flu_skill(flu_ev, flu_natural),
        "flu-reproducibility": flu_reproducibility(flu_ev, flu_replicate),
        "flu-by-jurisdiction": flu_by_jurisdiction(flu_ev),
        "covid-skill": covid_skill(covid_ev, covid_natural),
        "covid-reproducibility": covid_reproducibility(covid_ev, covid_replicate),
        "covid-by-state": covid_by_state(covid_ev),
    }
    missing = set(frames) ^ set(CAPTIONS)
    if missing:
        raise ValueError(f"every table needs a caption; mismatched: {sorted(missing)}")
    return {
        name: (frame, CAPTIONS[name], f"tab:{name}", NOTES.get(name))
        for name, frame in frames.items()
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--tables-dir", type=Path, default=OUTPUT_DIR,
        help=f"where to write; default {OUTPUT_DIR}",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="regenerate and compare against what is on disk; write nothing",
    )
    args = parser.parse_args(argv)

    use_manuscript_style()

    flu_ev = flu.load()
    flu_replicate = flu.load_replicate()

    covid_ev = covid.load()
    covid_replicate = covid.load_replicate()

    flu_natural = flu.load(scale="natural")
    covid_natural = covid.load(scale="natural")

    tables = build(
        flu_ev, flu_replicate, covid_ev, covid_replicate, flu_natural, covid_natural
    )

    if args.check:
        drifted = []
        for name, (frame, caption, label, note) in tables.items():
            for suffix, produced in (
                (".csv", frame.to_csv()),
                (".tex", _to_latex(frame, caption, label, note)),
            ):
                path = args.tables_dir / f"{name}{suffix}"
                if not path.exists():
                    drifted.append(f"{path.name}: missing")
                elif path.read_text() != produced:
                    drifted.append(f"{path.name}: differs from a fresh generation")
        if drifted:
            for problem in drifted:
                print(f"  {problem}")
            raise SystemExit(
                f"{len(drifted)} table(s) have drifted. Regenerate with "
                "`python -m manuscript_analysis.demos.tables`; never hand-edit them."
            )
        print(f"all {len(tables)} tables agree with a fresh generation")
        return

    args.tables_dir.mkdir(parents=True, exist_ok=True)
    for name, (frame, caption, label, note) in tables.items():
        csv_path = args.tables_dir / f"{name}.csv"
        tex_path = args.tables_dir / f"{name}.tex"
        csv_path.write_text(frame.to_csv())
        tex_path.write_text(_to_latex(frame, caption, label, note))
        print(f"wrote {csv_path}  ({len(frame)} rows)")
        print(f"wrote {tex_path}")


if __name__ == "__main__":
    main()
