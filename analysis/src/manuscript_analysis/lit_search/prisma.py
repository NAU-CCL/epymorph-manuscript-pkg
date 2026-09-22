"""Generate the PRISMA-style identification and selection flow.

Every number comes from `results/counts.json` and `decisions/packages.csv`; none is typed
here. That is the point. The two hand-maintained copies this replaces had drifted from each
other and from the appendix: for the same quantity, `prisma-flow.mermaid` said 21,
`prisma-flow.html` said 20, and Appendix S1.9 said 20 while the list beneath it named 22.

Writes both `results/prisma-flow.mermaid` (the source) and `results/prisma-flow.html` (a
self-contained viewer, for export to SVG/PNG).
"""
import csv
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

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
    figs["retained"] = decided["Include - Table 1"]
    figs["tabulated"] = sum(1 for row in marks if row["in_table_1"].strip() == "yes")
    figs["capsule_context"] = decided["Include - capsule"] + decided["Include - context"]
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

    S --> PF["Keyword pre-filter — one lexicon, both sources<br/>(software × inference × epidemiology)<br/>advanced n = {f['total_advanced']:,}<br/>({f['pubmed_advanced']:,} PubMed + {f['lens_advanced']:,} Lens)"]
    S --> EX["Set aside by pre-filter<br/>n = {f['total_dropped']:,}"]

    EX --> RA["Recall audit of set-aside records<br/>near-miss stratum empty by construction ·<br/>exhaustive package-title sweep n = {f['titlesweep']:,} ·<br/>seeded random sample n = {f['random_sample']:,} of {f['nocue_stratum']:,}<br/>→ 0 missed in-scope packages"]

    PF --> AS["Assessed for eligibility<br/>+ marks verified vs primary docs"]
    RA --> AS
    A2 --> AS

    AS --> INC["<b>Included</b><br/>{f['retained']} packages retained for comparison<br/>({f['tabulated']} tabulated in Table 1)<br/>{f['capsule_context']} capsule / context packages<br/>{f['references']} method / review references"]

    AS --> OOS["Excluded at eligibility<br/>agent-based only · Rt-only ·<br/>phylodynamics / genomics ·<br/>general-purpose toolkits · clinical models"]
"""


def html(diagram):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Figure S1 — Software identification &amp; selection flow</title>
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
    print(f"wrote {MERMAID.relative_to(paths.ROOT)} and {HTML.relative_to(paths.ROOT)}")
    print(f"  included: {f['retained']} retained ({f['tabulated']} tabulated), "
          f"{f['capsule_context']} capsule/context, {f['references']} references")


if __name__ == "__main__":
    main()
