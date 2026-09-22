"""
Build the candidate register workbook from the hand-maintained CSVs.

The 55 package rows and 34 CRAN task-view rows used to be Python list literals in
this file, which meant changing one package's disposition required editing source,
and meant a hand-edit to the .xlsx was destroyed the next time this ran. They now live
in `decisions/`, which nothing generates, and this script only formats.

    python3 src/register.py
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = Workbook()

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

# ================= Sheet 1: Register =================
def read_csv(path):
    """Header row and data rows from one of the hand-maintained decision files."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        sys.exit(f"{path} is empty")
    return rows[0], rows[1:]


ws1 = wb.active
ws1.title = "Register"
headers1, R = read_csv(paths.PACKAGES)

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
style_sheet(ws1, headers1, R, WIDTHS1[:len(headers1)],
            decision_col=1 + headers1.index("Decision"), decision_map=dmap)

# ================= Sheet 2: CRAN Task View enumeration =================
ws2 = wb.create_sheet("CRAN_Epi_enum")
headers2, C = read_csv(paths.CRAN_TASKVIEW)

style_sheet(ws2, headers2, C, [22,30,22,52])

# ================= Sheet 3: README =================
ws3 = wb.create_sheet("README")
readme = [
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
for row in readme:
    ws3.append(row)
ws3["A1"].font = Font(name="Arial", bold=True, size=13)
for r in range(2, len(readme)+1):
    ws3.cell(row=r, column=1).font = Font(name="Arial", bold=True, size=10)
    ws3.cell(row=r, column=2).font = BASE
    ws3.cell(row=r, column=2).alignment = wrap
for lbl in ["A7","A12","A18","A24","A29"]:
    ws3[lbl].font = Font(name="Arial", bold=True, size=11, color="1F4E78")
ws3.column_dimensions["A"].width = 26
ws3.column_dimensions["B"].width = 82

out = paths.REGISTER_XLSX
wb.save(out)
print("saved", out)
print("register rows:", len(R), "| cran enum rows:", len(C))
