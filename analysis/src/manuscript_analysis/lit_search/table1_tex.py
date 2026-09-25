r"""Emit Table 1 and Table S1 as LaTeX. Binary cells only: no partial marks.

Both tables are **projections of decisions/table-marks.csv**, not second sources of truth.
The worksheet keeps `*` where verification found the call hard; the tables ask sharper
questions so that every cell is binary, and the borderline cases are argued in S1's prose
instead. `DERIVED` and `DATA_ROWS` record, for each table row, which worksheet column it
comes from and how a `*` resolves. Running this script asserts the projection holds, so the
files cannot drift apart silently.

Rows with no worksheet column are listed in `TABLE_ONLY`, so that adding a row without
deciding its provenance fails the check rather than passing unnoticed.

Table 1 carries the 12 packages tabulated in the main text and omits the rows in `OMITTED`.

**Table S1 was removed from the manuscript on 2026-09-21 (JM): it duplicated Table 1.** The
appendix now carries the comparison in prose instead, in \S S1.3 and the capsules. The full
14-package grid is still written to `results/table-s1.tex` because it costs nothing and is
the obvious thing to hand a reviewer who asks to see every package on every criterion, but
**it is not part of the manuscript** and must not be pasted back in without deciding what it
adds that the prose does not.

Writes `results/table-1-maintext.tex` (goes in the manuscript) and `results/table-s1.tex`
(does not). Both regenerable and safe to delete, like everything else in `results/`. Never
hand-edit the installed copy: edit the worksheet and regenerate.

Regenerate:  python3 src/table1_tex.py   (or via run_all.py)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

# Package order, grouped by the role the software is designed for. `t1` marks the twelve
# tabulated in the main text; LibBi/rbi and epidemia are Table S1 only.
PKGS = [
    ("epymorph", "Pipelines", True),
    ("FlepiMoP", "Pipelines", True),
    ("MetaRVM", "Pipelines", True),
    ("spatPomp", "Toolkits", True),
    ("pomp", "Toolkits", True),
    ("odin/dust/mcstate", "Toolkits", True),
    ("LibBi/rbi", "Toolkits", False),
    ("pypfilt/epifx", "Toolkits", True),
    ("SimInf", "Simulation tools", True),
    ("PyRossGeo", "Simulation tools", True),
    ("surveillance (hhh4)", "Simulation tools", True),
    ("Epydemix", "Simulation tools", True),
    ("summer2/estival", "Simulation tools", True),
    ("epidemia", "Simulation tools", False),
]
NAMES = [p for p, _, _ in PKGS]
LANGUAGE = {
    "epymorph": "Python", "FlepiMoP": "Py/R", "MetaRVM": "R", "spatPomp": "R",
    "pomp": "R", "odin/dust/mcstate": "R", "LibBi/rbi": "C++/R", "pypfilt/epifx": "Python",
    "SimInf": "R", "PyRossGeo": "Python", "surveillance (hhh4)": "R",
    "Epydemix": "Python", "summer2/estival": "Python", "epidemia": "R",
}

# Marks, in PKGS order. "Y" is a filled circle; "" an empty one.
#           epy fle met | spa pom odi lib pyp | sim pyr hhh epy2 sum epi
ROWS = [
    ("GROUP", "Automated data acquisition"),
    ("Surveillance time series",
     ["Y", "Y", "", "", "", "", "", "", "", "", "", "", "", ""]),
    ("Population size and age structure",
     ["Y", "Y", "", "", "", "", "", "", "", "Y", "", "Y", "", ""]),
    ("Movement or commuting flows",
     ["Y", "Y", "", "", "", "", "", "", "", "", "", "", "", ""]),
    ("Age-stratified contact matrices",
     ["", "", "", "", "", "", "", "", "", "Y", "", "Y", "", ""]),
    ("Weather and environmental covariates",
     ["Y", "", "", "", "", "", "", "", "", "", "", "", "", ""]),
    ("Data for regions outside the United States",
     ["", "Y", "", "", "", "", "", "", "", "Y", "", "Y", "", ""]),

    ("GROUP", "Model specification"),
    ("Model specification language (DSL or declarative form)",
     ["Y", "Y", "", "", "", "Y", "Y", "", "Y", "", "", "Y", "Y", ""]),
    ("Automatic model diagrams and data-requirement analysis",
     ["Y", "", "", "", "", "", "", "", "", "", "", "", "", ""]),
    ("Ready-made compartmental models supplied",
     ["Y", "Y", "Y", "", "", "", "", "", "Y", "Y", "", "Y", "", ""]),

    ("GROUP", "Population structure"),
    ("Operator for demographic (age/risk) stratification",
     ["Y", "Y", "Y", "", "", "", "", "", "", "Y", "", "Y", "Y", ""]),
    ("Movement-based coupling between sub-populations",
     ["Y", "Y", "Y", "Y", "", "", "", "", "Y", "Y", "", "", "", ""]),

    ("GROUP", "Inference"),
    ("Probabilistic calibration and uncertainty quantification", ["Y"] * 14),
    ("Particle filter",
     ["Y", "", "", "Y", "Y", "Y", "Y", "Y", "Y", "", "", "", "", ""]),
    ("Ensemble Kalman filter",
     ["Y", "", "", "Y", "Y", "", "", "", "", "", "", "", "", ""]),

    ("GROUP", "Forecasting"),
    ("Forecast generation from a fitted model",
     ["Y", "Y", "", "", "", "Y", "Y", "Y", "", "Y", "Y", "Y", "", "Y"]),
    ("Forecast evaluation with proper scoring rules",
     ["", "", "", "", "", "", "", "Y", "", "", "Y", "", "", ""]),
    ("Data retrieval, fitting and forecasting in one package",
     ["Y", "Y", "", "", "", "", "", "", "", "", "", "", "", ""]),
]

# table row -> (worksheet column, {worksheet mark: table mark} resolutions)
DERIVED = {
    "Model specification language (DSL or declarative form)":
        ("Symbolic model specification", {"*": "Y"}),
    "Ready-made compartmental models supplied":
        ("Built-in epidemiological model library", {"*": ""}),
    "Operator for demographic (age/risk) stratification":
        ("Multi-strata (age/risk) composition", {"*": ""}),
    "Movement-based coupling between sub-populations":
        ("Geographic meta-population structure", {"*": ""}),
    "Probabilistic calibration and uncertainty quantification":
        ("Bayesian / probabilistic calibration & UQ (any method)", {}),
    "Particle filter": ("Particle filtering", {}),
    "Ensemble Kalman filter": ("Ensemble Kalman filtering", {}),
    "Forecast generation from a fitted model":
        ("Forecast generation from a fitted model", {}),
    "Forecast evaluation with proper scoring rules":
        ("Forecast evaluation (proper scoring rules)", {}),
}

# The six data rows all derive from the worksheet's one `Automated data handling` cell,
# which lists data types as text. Each row is filled iff its keyword appears there.
DATA_ROWS = {
    "Surveillance time series": "surveillance",
    "Population size and age structure": "population",
    "Movement or commuting flows": "commut",
    "Age-stratified contact matrices": "contact matri",
    "Weather and environmental covariates": "weather",
}

# Table-only refinements: no worksheet column speaks to these.
TABLE_ONLY = {
    "Automatic model diagrams and data-requirement analysis":
        "the other half of the split symbolic-specification row; only epymorph derives "
        "diagrams and data requirements from the symbolic form",
    "Data for regions outside the United States":
        "a coverage question the worksheet records only as prose inside the data cell",
    "Data retrieval, fitting and forecasting in one package":
        "a conjunction of worksheet rows rather than any single one",
}

# Rows the main text omits, and why. Table 1 carries the argument; Table S1 is the complete
# grid. Without a division like this the two tables are near-duplicates, which is a fair
# reviewer complaint and was JM's on 2026-09-21.
OMITTED = {
    "Forecast evaluation with proper scoring rules":
        "the forecast hubs score submissions with dedicated packages, so it is not a "
        "capability these packages are trying to have. Kept in Table S1, where hhh4 and "
        "pypfilt/epifx are the only filled marks.",
    "Probabilistic calibration and uncertainty quantification":
        "filled for all 14 packages, so it discriminates nothing; its content is one "
        "sentence of caption. Kept in Table S1 as the baseline it is.",
}
# The language row goes to Table S1 only: it is a minor attribute, and in Table 1 it is the
# single cause of the table overrunning the text width (20.1cm with it, 16.0cm without).
LANGUAGE_IN_TABLE_1 = False

CAPTION_T1 = (
    "\\textbf{Capabilities of epymorph and eleven other packages for mechanistic "
    "epidemic modeling and forecasting.} \\mkfull{}, the package provides a dedicated "
    "construct, API or data service for the capability; \\mknone{}, it does not. "
    "Additional packages are discussed in Supplementary "
    "\\S\\ref{sec:S1-3} and Table~\\ref{tab:S1}. Packages are grouped by the role they are "
    "designed for: \\emph{Pipelines}, end-to-end; \\emph{Toolkits}, inference toolkits; "
    "\\emph{Simulation tools}, simulation and calibration."
    "\\textsuperscript{a}One package that retrieves both the model inputs and the "
    "observation (i.e., surveillance) target, fits the model to them, and generates forecasts."
)

CAPTION_S1 = (
    "\\textbf{Feature comparison of the fourteen retained packages.} \\mkfull{}, the "
    "package provides a dedicated construct, API or data service for the capability; "
    "\\mknone{}, it does not. Each cell is a binary judgement against the criterion stated "
    "in \\S\\ref{sec:S1-3}; borderline calls are argued there rather than softened into a "
    "third symbol. Packages are grouped by the role they are designed for. This is the "
    "complete grid. Table~1 of the main text shows the twelve packages and the subset of "
    "capabilities that carry the argument; this table adds LibBi/rbi and epidemia, the "
    "probabilistic-calibration baseline that all fourteen satisfy, forecast evaluation, and "
    "the implementation language. \\textsuperscript{a}One package that retrieves both the model "
    "inputs and the calibration target, fits the model to them, and generates forecasts."
)


def check_against_worksheet():
    """Assert the tables are the projection of decisions/table-marks.csv they claim to be."""
    import csv
    ws = {r["package"]: r for r in
          csv.DictReader(paths.TABLE_MARKS.open(encoding="utf-8-sig"))}
    missing = [p for p in NAMES if p not in ws]
    assert not missing, f"packages absent from the worksheet: {missing}"
    assert len(ws) == len(NAMES), f"worksheet has {len(ws)} packages, tables have {len(NAMES)}"

    rows = {label: payload for label, payload in ROWS if label != "GROUP"}
    for label, payload in rows.items():
        assert len(payload) == len(NAMES), f"{label!r} has {len(payload)} marks"
    unaccounted = set(rows) - set(DERIVED) - set(DATA_ROWS) - set(TABLE_ONLY)
    assert not unaccounted, (
        "table rows with no recorded provenance: %s. Add each to DERIVED, DATA_ROWS or "
        "TABLE_ONLY." % sorted(unaccounted))

    problems = []
    for label, (column, resolve) in DERIVED.items():
        for pkg, got in zip(NAMES, rows[label]):
            mark = ws[pkg][column]
            want = resolve.get(mark, {"Yes": "Y", "No": ""}.get(mark, "?!"))
            if want != got:
                problems.append(
                    f"  {label!r} / {pkg}: worksheet {column!r}={mark!r} projects to "
                    f"{want!r}, table has {got!r}")
    for label, keyword in DATA_ROWS.items():
        for pkg, got in zip(NAMES, rows[label]):
            listed = keyword in ws[pkg]["Automated data handling"].lower()
            if ("Y" if listed else "") != got:
                problems.append(
                    f"  {label!r} / {pkg}: worksheet data cell "
                    f"{'lists' if listed else 'omits'} {keyword!r}, table has {got!r}")
    if problems:
        raise SystemExit("the tables have drifted from decisions/table-marks.csv:\n"
                         + "\n".join(problems))
    n = len(DERIVED) + len(DATA_ROWS)
    print(f"  projection check: {n} of {len(rows)} rows derive from the worksheet and "
          f"agree; {len(TABLE_ONLY)} are table-only")


def groups(names):
    """Contiguous (label, span) runs of the role grouping, for the given subset."""
    out = []
    for name in names:
        label = next(g for p, g, _ in PKGS if p == name)
        if out and out[-1][0] == label:
            out[-1][1] += 1
        else:
            out.append([label, 1])
    return [(label, span) for label, span in out]


def render(names, caption, label, rows, env, first_col, language):
    """Emit one table. `env` is the float environment; `first_col` the label column spec."""
    mark = {"Y": "\\mkfull{}", "": "\\mknone{}"}
    keep = [NAMES.index(n) for n in names]
    out = []
    A = out.append
    A(f"% GENERATED by software-lit-search/src/table1_tex.py -- do not hand-edit.")
    A(f"% Source of truth: software-lit-search/decisions/table-marks.csv")
    A(f"\\begin{{{env}}}[tb]")
    A("\\centering")
    A(f"\\caption{{{caption}}}")
    A(f"\\label{{{label}}}")
    A("\\footnotesize")
    A("\\setlength{\\tabcolsep}{3.5pt}")
    A("\\renewcommand{\\arraystretch}{1.1}")
    A(f"\\begin{{tabular}}{{@{{}}{first_col}{'c' * len(names)}@{{}}}}")
    A("\\toprule")

    head, rules, col = [""], [], 2
    for glabel, span in groups(names):
        head.append("\\multicolumn{%d}{c}{\\emph{\\scriptsize %s}}" % (span, glabel))
        side = "r" if col == 2 else ("l" if col + span - 1 == len(names) + 1 else "lr")
        rules.append("\\cmidrule(%s){%d-%d}" % (side, col, col + span - 1))
        col += span
    A(" & ".join(head) + " \\\\")
    A("".join(rules))
    A(" & ".join([""] + ["\\rotatebox{90}{%s}" % n for n in names]) + " \\\\")
    A("\\midrule")

    first = True
    for rlabel, payload in rows:
        if rlabel == "GROUP":
            if not first:
                A("\\addlinespace[3pt]")
            A("\\multicolumn{%d}{@{}l}{\\textbf{%s}} \\\\" % (len(names) + 1, payload))
            first = False
            continue
        text = rlabel
        if rlabel == "Data retrieval, fitting and forecasting in one package":
            text += "\\textsuperscript{a}"
        A(" & ".join(["\\quad " + text] + [mark[payload[i]] for i in keep]) + " \\\\")

    if language:
        A("\\midrule")
        A(" & ".join(["\\quad Language"] + [language[n] for n in names]) + " \\\\")
    A("\\bottomrule")
    A("\\end{tabular}")
    A(f"\\end{{{env}}}")
    return "\n".join(out) + "\n"


def main():
    check_against_worksheet()
    paths.RESULTS.mkdir(parents=True, exist_ok=True)

    t1_names = [p for p, _, t1 in PKGS if t1]
    t1_rows = [(a, b) for a, b in ROWS if a not in OMITTED]
    paths.TABLE1_TEX.write_text(
        render(t1_names, CAPTION_T1, "tab:comparison", t1_rows,
               "table*", "l", LANGUAGE if LANGUAGE_IN_TABLE_1 else None),
        encoding="utf-8")
    paths.TABLE_S1_TEX.write_text(
        render(NAMES, CAPTION_S1, "tab:S1", ROWS,
               "table", "l", LANGUAGE),
        encoding="utf-8")

    for f in (paths.TABLE1_TEX, paths.TABLE_S1_TEX):
        print(f"  wrote {f.relative_to(paths.ROOT)}")
    for label, payload in ROWS:
        if label != "GROUP":
            print(f"  {payload.count('Y'):2d}/14  {label}")


if __name__ == "__main__":
    main()
