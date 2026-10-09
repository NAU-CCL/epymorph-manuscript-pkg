"""
Build the candidate register workbook from the hand-maintained CSVs.

The 55 package rows and 34 CRAN task-view rows used to be Python list literals in
this file, which meant changing one package's disposition required editing source,
and meant a hand-edit to the .xlsx was destroyed the next time this ran. They now live
in `decisions/`, which nothing generates, and this module only formats.
"""
import csv
import io
import re
import sys
import zipfile

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from . import paths

# ---------- styles ----------
HDR = Font(name="Arial", bold=True, color="FFFFFF", size=11)
BASE = Font(name="Arial", size=10)
hdr_fill = PatternFill("solid", fgColor="1F4E78")
wrap = Alignment(vertical="top", wrap_text=True)
top = Alignment(vertical="top")
thin = Side(style="thin", color="D9D9D9")
border = Border(left=thin, right=thin, top=thin, bottom=thin)

fills = {
    "t1":  PatternFill("solid", fgColor="C6EFCE"),  # Include - Table 1 (green)
    "ctx": PatternFill("solid", fgColor="DDEBF7"),  # Include - context/capsule (blue)
    "cand":PatternFill("solid", fgColor="FFF2CC"),  # Candidate - verify (yellow)
    "exc": PatternFill("solid", fgColor="F2F2F2"),  # Exclude (grey)
}

def style_sheet(ws, headers, rows, widths, decision_col=None, decision_map=None):
    ws.append(headers)
    for c in range(1, len(headers)+1):
        cell = ws.cell(row=1, column=c)
        cell.font = HDR; cell.fill = hdr_fill; cell.alignment = wrap; cell.border = border
    for r in rows:
        ws.append(r)
    for ri in range(2, len(rows)+2):
        for ci in range(1, len(headers)+1):
            cell = ws.cell(row=ri, column=ci)
            cell.font = BASE; cell.alignment = wrap; cell.border = border
        if decision_col and decision_map:
            key = decision_map(ws.cell(row=ri, column=decision_col).value)
            if key:
                for ci in range(1, len(headers)+1):
                    ws.cell(row=ri, column=ci).fill = fills[key]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"


def read_csv(path):
    """Header row and data rows from one of the hand-maintained decision files."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        sys.exit(f"{path} is empty")
    return rows[0], rows[1:]


# Row shading by disposition. Recovered from the baseline workbook's own fills rather
# than guessed: "Reference (cite)" is deliberately unshaded, every "Include - ..." other
# than Table 1 shares the context blue, and both Exclude variants share the grey.
def dmap(value):
    value = value or ""
    if value.startswith("Include - Table 1"):
        return "t1"
    if value.startswith("Include"):
        return "ctx"
    if value.startswith("Candidate"):
        return "cand"
    if value.startswith("Exclude"):
        return "exc"
    return None


WIDTHS1 = [20, 13, 20, 26, 34, 10, 16, 20, 30, 40, 26, 30, 34, 30]

README = [
["Software candidate register - epymorph mini-review (Appendix S1)"],
[""],
["Purpose","Living screening register for the structured software search. One row per package."],
["Verification date","2026-07-07 (first pass)"],
["Protocol","See drafts/appendix-software-landscape.md, section S1.1 (search string, criteria)."],
[""],
["HOW TO USE"],
["1","Add a row on 'Register' for any package you find. Fill Sources/URL/methods."],
["2","Set Decision to one of: Include - Table 1 / Include - context / Include - capsule / Candidate - verify / Exclude."],
["3","Row color follows Decision automatically only for existing rows; recolor new rows to match legend if desired."],
["4","'CRAN_Epi_enum' = full enumeration of the CRAN Epidemiology Task View modeling packages that were screened (the visible registry return)."],
[""],
["LEGEND (Decision)"],
["Include - Table 1","Green - tabulated as a competitor column"],
["Include - context / capsule","Blue - mentioned in S1.5 or as a capsule, not tabulated"],
["Include - capsule","Yellow - epi-specific; needs a decision (column vs capsule) or doc verification"],
["Exclude","Grey - out of scope; reason recorded"],
[""],
["DIVISION OF LABOR (what is done vs. still manual)"],
["Done by assistant","Registry enumeration (CRAN Task View), targeted GitHub, feature-mark verification vs primary docs, this register."],
["Still manual (you/co-author)","Google Scholar + Scopus/Web of Science + PubMed runs with the locked strings, to obtain complete, countable, exportable results. Append new hits here."],
["Reason","Search tools return only top hits, not full exportable database result sets; paywalled databases need institutional access."],
[""],
["OPEN ITEMS"],
["a","Decide epidemia (and SimBIID/Pathogen.jl/BayesianFitForecast/Bernadette/epinet) as columns vs capsules."],
["b","Verify MEmilio built-in inference/filtering before any tabulation."],
["c","Finalize retrieval counts via Scholar/Scopus/WoS for the screening log."],
]


def build():
    """The workbook's three sheets: Register, CRAN_Epi_enum, README."""
    wb = Workbook()

    ws1 = wb.active
    ws1.title = "Register"
    headers1, R = read_csv(paths.PACKAGES)
    style_sheet(ws1, headers1, R, WIDTHS1[:len(headers1)],
                decision_col=1 + headers1.index("Decision"), decision_map=dmap)

    ws2 = wb.create_sheet("CRAN_Epi_enum")
    headers2, C = read_csv(paths.CRAN_TASKVIEW)
    style_sheet(ws2, headers2, C, [22,30,22,52])

    ws3 = wb.create_sheet("README")
    for row in README:
        ws3.append(row)
    ws3["A1"].font = Font(name="Arial", bold=True, size=13)
    for r in range(2, len(README)+1):
        ws3.cell(row=r, column=1).font = Font(name="Arial", bold=True, size=10)
        ws3.cell(row=r, column=2).font = BASE
        ws3.cell(row=r, column=2).alignment = wrap
    for lbl in ["A7","A12","A18","A24","A29"]:
        ws3[lbl].font = Font(name="Arial", bold=True, size=11, color="1F4E78")
    ws3.column_dimensions["A"].width = 26
    ws3.column_dimensions["B"].width = 82
    return wb, len(R), len(C)


# openpyxl stamps the save time into the workbook's properties and into every entry of the
# zip it writes, so two builds of identical content would differ byte for byte. Rebuild the
# zip with one fixed time, so the file changes only when its content does.
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)  # the zip format's epoch: a conventional "no date"
FIXED_STAMP = b"1980-01-01T00:00:00Z"


def pinned_bytes(wb):
    """The saved workbook, with every timestamp in it fixed."""
    built = io.BytesIO()
    wb.save(built)
    pinned = io.BytesIO()
    with zipfile.ZipFile(built) as source, zipfile.ZipFile(pinned, "w") as target:
        for entry in source.infolist():
            data = source.read(entry.filename)
            if entry.filename == "docProps/core.xml":
                data = re.sub(rb'(W3CDTF">)[^<]*(<)', rb"\g<1>" + FIXED_STAMP + rb"\g<2>", data)
            fixed = zipfile.ZipInfo(entry.filename, date_time=FIXED_ZIP_TIME)
            fixed.compress_type = entry.compress_type
            fixed.external_attr = entry.external_attr
            target.writestr(fixed, data)
    return pinned.getvalue()


def main(check=False):
    wb, packages, cran = build()
    rebuilt = pinned_bytes(wb)
    out = paths.REGISTER_XLSX
    # Check 7: with `check`, the register must rebuild from the decisions unchanged. A
    # difference fails and leaves the file alone, so the failure repeats until someone looks;
    # a run without `check` (`just build`) is how a deliberate change to the decisions is
    # written.
    if check and out.exists() and out.read_bytes() != rebuilt:
        sys.exit(f"{out.name} does not match a rebuild from {paths.PACKAGES.name} and "
                 f"{paths.CRAN_TASKVIEW.name}: hand-edited, or the decisions changed since "
                 "it was last built. Run `just build` to rebuild it.")
    out.write_bytes(rebuilt)
    print("saved", out)
    print("register rows:", packages, "| cran enum rows:", cran)
