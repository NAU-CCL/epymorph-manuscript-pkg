"""Build Word copies of the manuscript and supplement for collaborators to comment on.

    python -m manuscript_analysis.build_docx          (or scripts/build-docx.sh)

Writes `results/manuscript-docx/epymorph-ms_main_<date>.docx` and
`..._supplement_<date>.docx`, ready to drop into a Team or OneDrive folder.

The source is the Overleaf clone, because that is exactly what collaborators see in
Overleaf. The conversion is pandoc's, after a few repairs pandoc cannot make on its own.
Every repair is made to a staged copy in a temporary folder; nothing in the Overleaf clone
or in `manuscript/` is touched.

  - Front matter. The journal class's \\author, \\affil and \\abstract commands are rewritten
    as a plain title block, author list, affiliations and abstract.
  - Numbering. pandoc numbers neither captions nor cross-references, so this walks the
    document in reading order, numbers sections, figures and tables the way LaTeX would
    (S-prefixed in the supplement), writes "Figure 2." into each caption, and replaces every
    \\ref with its number.
  - Figures. Word cannot display a PDF, so each PDF figure is swapped for the PNG copy that
    the figure exporter writes beside it in `results/`.
  - Tables. Table 1's circles become the characters they draw, and the generated tables'
    two-line headers (a nested tabular pandoc cannot parse) become one line.

A Word copy is for comments on the text, and it is one-way: changes are made in Overleaf.
The compiled PDF stays the authoritative version of every figure and table.
"""
import datetime
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OVERLEAF = Path(os.environ.get(
    "OVERLEAF", Path.home() / "Documents" / "Claude" / "Projects" / "epymorph_ms_overleaf"
))
OUTPUT_DIR = ROOT / "results" / "manuscript-docx"

# Where the PNG twin of each PDF figure lives. The figure exporters write both formats.
PNG_SOURCES = [
    ROOT / "results" / "demos" / "figures",
    ROOT / "results" / "lit-search",
]

# The two documents, and the prefix their figure, table and section numbers carry.
DOCUMENTS = {
    "main": {"source": "main.tex", "prefix": ""},
    "supplement": {"source": "supplement.tex", "prefix": "S"},
}


# --- Reading LaTeX ----------------------------------------------------------------------


def braced(text: str, start: int) -> tuple[str, int]:
    """The contents of the brace group opening at `text[start]`, and the index after it."""
    if text[start] != "{":
        raise ValueError(f"expected '{{' at {start}, found {text[start]!r}")
    depth = 0
    for position in range(start, len(text)):
        character = text[position]
        if character == "\\":
            continue
        if character == "{" and text[position - 1] != "\\":
            depth += 1
        elif character == "}" and text[position - 1] != "\\":
            depth -= 1
            if depth == 0:
                return text[start + 1:position], position + 1
    raise ValueError(f"unbalanced braces from {start}")


def command_argument(text: str, command: str) -> str | None:
    """The braced argument of the first `\\command[...]{...}` or `\\command*{...}`."""
    match = re.search(r"\\" + command + r"\*?(\[[^\]]*\])?\{", text)
    if match is None:
        return None
    contents, _ = braced(text, match.end() - 1)
    return contents


def strip_comments(text: str) -> str:
    """Drop LaTeX comments: from an unescaped % to the end of its line."""
    return re.sub(r"(?<!\\)%.*", "", text)


def expand_inputs(text: str, base: Path) -> str:
    """Replace each \\input{name} with that file's text, recursively, comments removed."""
    def replace(match):
        name = match.group(1)
        path = base / (name if name.endswith(".tex") else f"{name}.tex")
        return expand_inputs(strip_comments(path.read_text(encoding="utf-8")), base)
    return re.sub(r"\\input\{([^}]+)\}", replace, text)


def plain(latex: str) -> str:
    """Strip the formatting commands front matter uses, keeping their text."""
    text = re.sub(r"\\(orgdiv|orgname|orgaddress|city|state|country|fnm|sur)\{", "{", latex)
    text = text.replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", text).strip()


# --- Front matter -----------------------------------------------------------------------


def front_matter(main: str) -> str:
    """The journal class's title block, rewritten as plain LaTeX that pandoc understands."""
    title = command_argument(main, "title")

    authors = []
    for match in re.finditer(r"\\author(\*?)\[([^\]]*)\]\{", main):
        name, _ = braced(main, match.end() - 1)
        corresponding = "*" if match.group(1) else ""
        authors.append(f"{plain(name)}$^{{{match.group(2)}{corresponding}}}$")

    affiliations = []
    for match in re.finditer(r"\\affil\*?\[([^\]]*)\]\{", main):
        affiliation, _ = braced(main, match.end() - 1)
        affiliations.append(f"$^{{{match.group(1)}}}$ {plain(affiliation)}")

    email = command_argument(main, "email")
    abstract = command_argument(main, "abstract")
    keywords = command_argument(main, "keywords")

    lines = [
        f"\\title{{{title}}}",
        f"\\author{{{', '.join(authors)}}}",
        "\\date{}",
        "\\maketitle",
        "",
        "\\begin{abstract}",
        abstract,
        "\\end{abstract}",
        "",
        "\\noindent " + " \\\\\n".join(affiliations),
        "",
        f"\\noindent $^*$Corresponding author: {email}",
        "",
        f"\\noindent \\textbf{{Keywords:}} {keywords}",
        "",
    ]
    return "\n".join(lines)


def main_body(main: str) -> str:
    """Everything after \\maketitle, with the journal class's back-matter commands made plain."""
    body = main[main.index("\\maketitle") + len("\\maketitle"):]
    body = body[:body.index("\\end{document}")]
    body = body.replace("\\backmatter", "")
    body = re.sub(r"\\bmhead\{([^}]*)\}", r"\\section*{\1}", body)
    body = re.sub(r"\\bibliography\{[^}]*\}", "", body)
    return body


def supplement_parts(supplement: str) -> tuple[str, str]:
    """The supplement's title and its body, for the same plain document shape as the paper."""
    title = command_argument(supplement, "title")
    title = re.sub(r"\\\\(\[[^\]]*\])?", " ", title).replace("\\large", "")
    title = re.sub(r"\s+", " ", title).strip()
    body = supplement[supplement.index("\\maketitle") + len("\\maketitle"):]
    body = body[:body.index("\\end{document}")]
    body = re.sub(r"\\bibliography(style)?\{[^}]*\}", "", body)
    return title, body


# --- Numbering --------------------------------------------------------------------------

NUMBERED = re.compile(
    r"\\(?P<heading>section|subsection|subsubsection)(?P<star>\*?)\{"
    r"|\\begin\{(?P<float>figure|table|longtable|equation)\*?\}"
    r"|\\label\{(?P<label>[^}]+)\}"
    r"|\\caption\{"
)


def number_document(text: str, prefix: str) -> tuple[str, dict]:
    """Number sections, figures and tables in reading order, as LaTeX would.

    Returns the text with "Figure N." / "Table N." written into each caption, and a map
    from every \\label to the number a \\ref to it should print.
    """
    sections = [0, 0, 0]
    counts = {"figure": 0, "table": 0, "equation": 0}
    current = None          # the number the next \label belongs to
    current_kind = None     # "figure", "table" or None, for the next \caption
    numbers = {}
    insertions = []         # (position, text) to add after each "\caption{"

    for match in NUMBERED.finditer(text):
        if match.group("heading"):
            if match.group("star"):
                continue
            level = ["section", "subsection", "subsubsection"].index(match.group("heading"))
            sections[level] += 1
            for deeper in range(level + 1, 3):
                sections[deeper] = 0
            current = prefix + ".".join(str(n) for n in sections[:level + 1])
            current_kind = None
        elif match.group("float"):
            kind = "table" if match.group("float") == "longtable" else match.group("float")
            counts[kind] += 1
            if kind == "equation":
                current = str(counts[kind])
                current_kind = None
            else:
                current = f"{prefix}{counts[kind]}"
                current_kind = kind
        elif match.group("label"):
            numbers[match.group("label")] = current
        elif current_kind is not None:
            name = "Figure" if current_kind == "figure" else "Table"
            insertions.append((match.end(), f"{name} {current}. "))

    for position, label in reversed(insertions):
        text = text[:position] + label + text[position:]
    return text, numbers


def resolve_references(text: str, numbers: dict, outside: dict) -> str:
    """Replace each \\ref with its number. A label from the other document keeps its number
    too, so the supplement can cite main-text figures and vice versa."""
    known = {**outside, **numbers}

    def replace(match):
        label = match.group(1)
        return known.get(label, f"[{label}]")
    text = re.sub(r"\\S\\ref\{([^}]+)\}", lambda m: "Section " + replace(m), text)
    return re.sub(r"\\ref\{([^}]+)\}", replace, text)


# --- Figures and tables -------------------------------------------------------------------


def stage_figures(text: str, stage: Path) -> tuple[str, list[str]]:
    """Copy each figure into the staging folder, as a PNG where Word or pandoc needs one.

    A PDF figure is swapped for its PNG twin, because Word cannot display a PDF. A JPEG is
    re-saved as an RGB PNG, because pandoc cannot read the size of a CMYK JPEG (Fig. 1 is
    one) and falls back to a fixed 4 x 2.67 inch box, stretching the image.
    """
    figures = stage / "figures"
    figures.mkdir(exist_ok=True)
    problems = []

    def replace(match):
        options, path = match.group(1) or "", match.group(2)
        source = OVERLEAF / path
        if source.suffix == ".pdf":
            twins = [folder / f"{source.stem}.png" for folder in PNG_SOURCES]
            found = [twin for twin in twins if twin.exists()]
            if not found:
                problems.append(f"no PNG copy of {path}; Word will not display it")
            else:
                source = found[0]
        if not source.exists():
            problems.append(f"figure not found: {path}")
            return match.group(0)
        if source.suffix.lower() in (".jpg", ".jpeg"):
            staged = figures / f"{source.stem}.png"
            Image.open(source).convert("RGB").save(staged, dpi=(300, 300))
        else:
            staged = figures / source.name
            shutil.copy(source, staged)
        return f"\\includegraphics{options}{{figures/{staged.name}}}"

    text = re.sub(r"\\includegraphics(\[[^\]]*\])?\{([^}]+)\}", replace, text)
    return text, problems


def simplify_tables(text: str) -> str:
    """Repair the table constructs pandoc cannot read."""
    # Table 1 spans both columns as a table*; pandoc drops a table*'s caption.
    text = text.replace("\\begin{table*}", "\\begin{table}").replace("\\end{table*}", "\\end{table}")
    text = text.replace("\\mkfull{}", "●").replace("\\mknone{}", "○")
    text = re.sub(r"\\rotatebox\{[^}]*\}\{([^}]*)\}", r"\1", text)
    # A two-line generated header: \begin{tabular}[b]{@{}r@{}}\textbf{a} \\ \textbf{b}\end{tabular}
    text = re.sub(
        r"\\begin\{tabular\}\[b\]\{@\{\}r@\{\}\}\\textbf\{([^}]*)\} \\\\ \\textbf\{([^}]*)\}"
        r"\\end\{tabular\}",
        r"\\textbf{\1 \2}",
        text,
    )
    # "@{}" trims a column's outer padding; pandoc misreads it inside a column spec.
    text = text.replace("@{}", "")
    text = re.sub(r"\\addlinespace(\[[^\]]*\])?", "", text)
    text = re.sub(r"\\cmidrule(\([^)]*\))?\{[^}]*\}", "", text)
    # A blank line is a paragraph break, which ends a table as far as pandoc is concerned;
    # removing the commands above can leave one behind.
    text = re.sub(
        r"\\begin\{(tabular|longtable)\}.*?\\end\{\1\}",
        lambda match: re.sub(r"\n\s*\n", "\n", match.group(0)),
        text,
        flags=re.S,
    )
    return text


# --- Building ---------------------------------------------------------------------------


def overleaf_commit() -> str:
    """The Overleaf clone's commit, and whether it has uncommitted changes."""
    commit = subprocess.run(
        ["git", "-C", str(OVERLEAF), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "-C", str(OVERLEAF), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return commit + (" plus uncommitted edits" if dirty else "")


def assemble(name: str) -> str:
    """One document as plain LaTeX, ready for pandoc."""
    source = strip_comments((OVERLEAF / DOCUMENTS[name]["source"]).read_text(encoding="utf-8"))
    if name == "main":
        head = front_matter(source)
        body = main_body(source)
    else:
        title, body = supplement_parts(source)
        head = "\n".join([f"\\title{{{title}}}", "\\date{}", "\\maketitle", ""])
    body = expand_inputs(body, OVERLEAF)
    return (
        "\\documentclass{article}\n\\begin{document}\n"
        + head
        + body
        + "\n\\section*{References}\n\\end{document}\n"
    )


def build() -> list[Path]:
    today = datetime.date.today().isoformat()
    commit = overleaf_commit()
    # Which version this is, kept out of the text: it goes in the file's document
    # properties (File > Properties in Word), where it stays traceable without being read.
    provenance = f"Built {today} from Overleaf commit {commit}"

    # Number both documents first, so each can resolve the other's labels.
    assembled = {name: assemble(name) for name in DOCUMENTS}
    numbered = {}
    labels = {}
    for name, text in assembled.items():
        numbered[name], labels[name] = number_document(text, DOCUMENTS[name]["prefix"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for name in DOCUMENTS:
        other = {label: number for doc, found in labels.items() if doc != name
                 for label, number in found.items()}
        text = resolve_references(numbered[name], labels[name], other)
        text = simplify_tables(text)

        with tempfile.TemporaryDirectory() as folder:
            stage = Path(folder)
            text, problems = stage_figures(text, stage)
            (stage / "document.tex").write_text(text, encoding="utf-8")
            shutil.copy(OVERLEAF / "references.bib", stage / "references.bib")

            output = OUTPUT_DIR / f"epymorph-ms_{name}_{today}.docx"
            result = subprocess.run(
                ["pandoc", "document.tex", "--from", "latex", "--citeproc",
                 "--bibliography", "references.bib",
                 "--metadata", f"description={provenance}",
                 "--output", str(output)],
                cwd=stage, capture_output=True, text=True,
            )
        if result.returncode != 0:
            raise SystemExit(f"pandoc failed on the {name} document:\n{result.stderr}")

        warnings = [line for line in result.stderr.splitlines() if line.strip()]
        unresolved = sorted(set(re.findall(r"\[((?:fig|tab|sec|eq):[^\]]+)\]", text)))
        print(f"wrote {output.relative_to(ROOT)}")
        for problem in problems:
            print(f"  note: {problem}")
        for label in unresolved:
            print(f"  note: unresolved reference {label}")
        math = sum("Could not convert TeX math" in line for line in warnings)
        if math:
            print(f"  note: {math} equation(s) kept as LaTeX source; see the PDF for these")
        written.append(output)
    return written


if __name__ == "__main__":
    print(f"source: {OVERLEAF} (commit {overleaf_commit()})")
    build()
