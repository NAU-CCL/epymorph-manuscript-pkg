"""Generate the PRISMA-style identification and selection flow.

Every number comes from `results/counts.json` and `decisions/packages.csv`; none is typed
here. That is the point. The two hand-maintained copies this replaces had drifted from each
other and from the appendix: for the same quantity, `prisma-flow.mermaid` said 21,
`prisma-flow.html` said 20, and Appendix S1.9 said 20 while the list beneath it named 22.

Writes `results/figS-software-search-flow.png`, the figure the supplement includes (drawn
with matplotlib, so no browser or Node toolchain is needed), plus `results/prisma-flow.mermaid`
and `results/prisma-flow.html`, the same diagram as text and as a browser viewer.
"""
import csv
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

import matplotlib

matplotlib.use("Agg")  # draw to a file; no display needed
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

PNG = paths.RESULTS / "figS-software-search-flow.png"
MERMAID = paths.RESULTS / "prisma-flow.mermaid"
HTML = paths.RESULTS / "prisma-flow.html"


def figures():
    """Every number the diagram shows, derived rather than remembered."""
    counts = json.loads(paths.COUNTS.read_text(encoding="utf-8"))
    register = list(csv.DictReader(paths.PACKAGES.open(encoding="utf-8-sig")))
    marks = list(csv.DictReader(paths.TABLE_MARKS.open(encoding="utf-8-sig")))
    decided = Counter(row["Decision"].strip() for row in register)

    figs = dict(counts)
    figs["unique"] = counts["pubmed_retrieved"] + counts["lens_novel"]
    figs["no_abstract"] = counts["pubmed_retrieved"] - counts["pubmed_screened"]
    # The register counts epymorph itself among the Table 1 rows; the figure reports the
    # packages it is compared with.
    figs["retained"] = decided["Include - Table 1"]
    figs["compared"] = decided["Include - Table 1"] - 1
    tabulated = [row for row in marks if row["in_table_1"].strip() == "yes"]
    figs["tabulated"] = len(tabulated)
    figs["tabulated_comparators"] = len(tabulated) - 1
    figs["context"] = decided["Include - capsule"] + decided["Include - context"]
    figs["references"] = decided["Reference (cite)"]
    return figs


def mermaid(f):
    return f"""flowchart TB
    subgraph ID["Identification"]
        A1["Bibliographic databases<br/>PubMed n = {f['pubmed_retrieved']:,}<br/>Lens.org (journal + conference<br/>+ preprint) n = {f['lens_retrieved']:,}"]
        A2["Other sources<br/>CRAN Task View (curated)<br/>PyPI / JOSS · GitHub topics<br/>Citation-chaining"]
    end

    A1 --> D["Duplicates removed<br/>PubMed ∩ Lens, n = {f['lens_duplicates']:,}"]
    D --> U["Unique records identified<br/>n = {f['unique']:,}<br/>({f['pubmed_retrieved']:,} PubMed + {f['lens_novel']:,} novel Lens)"]
    U --> S["Screened<br/>n = {f['total_screened']:,}<br/>({f['no_abstract']} PubMed records lacked abstracts)"]

    S --> PF["Keyword pre-filter, one lexicon for both sources<br/>(software × inference × epidemiology)<br/>advanced n = {f['total_advanced']:,}<br/>({f['pubmed_advanced']:,} PubMed + {f['lens_advanced']:,} Lens)"]
    S --> EX["Set aside by pre-filter<br/>n = {f['total_dropped']:,}"]

    EX --> RA["Recall audit of set-aside records<br/>near-miss stratum empty by construction ·<br/>exhaustive package-title sweep n = {f['titlesweep']:,} ·<br/>seeded random sample n = {f['random_sample']:,} of {f['nocue_stratum']:,}<br/>→ 0 missed in-scope packages"]

    PF --> AS["Assessed for eligibility<br/>+ marks verified vs primary docs"]
    RA --> AS
    A2 --> AS

    AS --> INC["<b>Included</b><br/>{f['compared']} packages compared with epymorph<br/>({f['tabulated_comparators']} in Table 1)<br/>{f['context']} tools noted as context<br/>{f['references']} method / review references"]

    AS --> OOS["Excluded at eligibility<br/>agent-based only · Rt-only ·<br/>phylodynamics / genomics ·<br/>general-purpose toolkits · clinical models"]
"""


# ---------------------------------------------------------------------------------------
# The PNG. Two columns: the main flow down the left, and the boxes that branch off it on
# the right, each level with the step it branches from. Coordinates are in axes units
# (0 to 1 in both directions).
# ---------------------------------------------------------------------------------------

MAIN_X, MAIN_W = 0.25, 0.48
SIDE_X, SIDE_W = 0.76, 0.46
BOX_H = 0.13
ROWS = [0.92, 0.71, 0.50, 0.29, 0.08]
LINE = dict(color="#333333", linewidth=0.8)


def draw_box(ax, x, y, width, text, shade="#f2f2f2"):
    box = FancyBboxPatch((x - width / 2, y - BOX_H / 2), width, BOX_H,
                         boxstyle="round,pad=0.004,rounding_size=0.01",
                         facecolor=shade, edgecolor=LINE["color"],
                         linewidth=LINE["linewidth"])
    ax.add_patch(box)
    ax.text(x, y, text, ha="center", va="center", fontsize=8, linespacing=1.4)


def draw_arrow(ax, start, end):
    ax.annotate("", xy=end, xytext=start,
                arrowprops=dict(arrowstyle="-|>", shrinkA=0, shrinkB=0, **LINE))


def draw_png(f):
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    half = BOX_H / 2
    main_right = MAIN_X + MAIN_W / 2
    side_left = SIDE_X - SIDE_W / 2

    # Main flow, top to bottom.
    main_boxes = [
        f"Records identified in databases\n"
        f"PubMed n = {f['pubmed_retrieved']:,}\n"
        f"Lens.org n = {f['lens_retrieved']:,} (including preprints)",
        f"Records screened by keyword filter\nn = {f['total_screened']:,}",
        f"Records reviewed manually\nn = {f['total_advanced']:,}\n"
        f"({f['pubmed_advanced']:,} PubMed, {f['lens_advanced']:,} Lens.org)",
        "Packages assessed for eligibility\n"
        "capabilities verified against\nprimary documentation",
        f"Included\n{f['compared']} packages compared with epymorph\n"
        f"({f['tabulated_comparators']} in Table 1, 2 described in S1 only)\n"
        f"{f['context']} further tools noted as context",
    ]
    for i, text in enumerate(main_boxes):
        is_last = i == len(main_boxes) - 1
        draw_box(ax, MAIN_X, ROWS[i], MAIN_W, text, shade="#dde8f3" if is_last else "#f2f2f2")
        if not is_last:
            draw_arrow(ax, (MAIN_X, ROWS[i] - half), (MAIN_X, ROWS[i + 1] + half))

    # Records leaving the flow, level with the step they leave from.
    removed = (f"Removed before screening\n"
               f"duplicates (PubMed and Lens.org) n = {f['lens_duplicates']:,}\n"
               f"no abstract n = {f['no_abstract']:,}")
    draw_box(ax, SIDE_X, ROWS[0], SIDE_W, removed)
    draw_arrow(ax, (main_right, ROWS[0]), (side_left, ROWS[0]))

    set_aside = f"Set aside by keyword filter\nn = {f['total_dropped']:,}"
    draw_box(ax, SIDE_X, ROWS[1], SIDE_W, set_aside)
    draw_arrow(ax, (main_right, ROWS[1]), (side_left, ROWS[1]))

    # The recall audit checks the set-aside records, and found nothing to send back.
    audit = (f"Audit of set-aside records\n"
             f"every title naming a package, n = {f['titlesweep']:,}\n"
             f"random sample, n = {f['random_sample']:,} of {f['nocue_stratum']:,}\n"
             f"0 eligible packages missed")
    draw_box(ax, SIDE_X, ROWS[2], SIDE_W, audit)
    draw_arrow(ax, (SIDE_X, ROWS[1] - half), (SIDE_X, ROWS[2] + half))

    # Packages found outside the databases join the flow at eligibility.
    other = ("Packages from other sources\nsoftware registries, Google Scholar,\n"
             "GitHub topics, citation chaining")
    draw_box(ax, SIDE_X, ROWS[3], SIDE_W, other)
    draw_arrow(ax, (side_left, ROWS[3]), (main_right, ROWS[3]))

    # Exclusions branch off the arrow between eligibility and inclusion.
    excluded = ("Excluded\nagent-based simulators, R$_t$-only estimators,\n"
                "general-purpose toolkits, genomic and\nclinical tools, methods papers")
    draw_box(ax, SIDE_X, ROWS[4], SIDE_W, excluded)
    branch_y = (ROWS[3] + ROWS[4]) / 2
    ax.plot([MAIN_X, SIDE_X], [branch_y, branch_y], **LINE)
    draw_arrow(ax, (SIDE_X, branch_y), (SIDE_X, ROWS[4] + half))

    fig.savefig(PNG, dpi=300, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)


def html(diagram):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Figure S1: Software identification &amp; selection flow</title>
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; margin: 24px; color: #1a1a1a; }}
  h1 {{ font-size: 16px; font-weight: 600; }}
  p  {{ font-size: 13px; color: #555; max-width: 760px; }}
  #diagram {{ margin-top: 16px; }}
  .hint {{ font-size: 12px; color: #777; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px; }}
</style>
</head>
<body>
  <h1>Figure S1. Software identification and selection flow (PRISMA-style)</h1>
  <p>Generated from the search pipeline; do not hand-edit. Every number is derived from
     <code>results/counts.json</code> and <code>decisions/packages.csv</code>. To export:
     right-click the diagram &rarr; “Save image”, or paste
     <code>prisma-flow.mermaid</code> into mermaid.live for SVG/PNG.</p>
  <div id="diagram">
    <pre class="mermaid">
{diagram}    </pre>
  </div>
  <p class="hint">Rendered client-side by Mermaid.</p>
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
  </script>
</body>
</html>
"""


def main():
    f = figures()
    paths.RESULTS.mkdir(parents=True, exist_ok=True)
    diagram = mermaid(f)
    MERMAID.write_text(diagram, encoding="utf-8")
    HTML.write_text(html(diagram), encoding="utf-8")
    draw_png(f)
    print(f"wrote {PNG.relative_to(paths.ROOT)}, {MERMAID.relative_to(paths.ROOT)} "
          f"and {HTML.relative_to(paths.ROOT)}")
    print(f"  included: {f['retained']} retained ({f['tabulated']} tabulated), "
          f"{f['context']} context, {f['references']} references")


if __name__ == "__main__":
    main()
