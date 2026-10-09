"""Small things the build and both demos' notebooks need that are neither epymorph nor
plotting: writing a table as LaTeX, and checking regenerated outputs against the committed
ones.
"""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

# --- tables as LaTeX ----------------------------------------------------------------
#
# Every .tex under results/ is a projection of a DataFrame, carries a header saying what
# generated it, and is never hand-edited. A booktabs tabular is a few lines, so it is
# written out here rather than through `DataFrame.to_latex` and its jinja2 dependency.

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


def to_latex(
    frame: pd.DataFrame,
    caption: str,
    label: str,
    note: str | None = None,
    *,
    generated_by: str,
    regenerate: str,
    long: bool = False,
    compact: bool = False,
) -> str:
    """One table, as a complete LaTeX environment ready to `\\input`.

    A full environment rather than a bare `tabular`: the caption is part of what is
    generated, so a number quoted in it cannot drift from the table beneath it. The first
    line says what generated the file, which `scripts/check.py` requires of every `.tex`.

    `long` sets a table too tall for one page as a `longtable`, which breaks across pages
    and repeats its header (the supplement loads the package). `compact` sets a table one
    size smaller, for one whose columns are still too wide at `\\footnotesize`.
    """
    header = [
        f"% GENERATED by {generated_by} -- do not hand-edit.",
        f"% Regenerate:  {regenerate}",
    ]
    if long:
        return "\n".join(header) + "\n" + _longtable(frame, caption, label, note) + "\n"

    body = _tabular(frame)
    lines = [
        *header,
        "\\begin{table}[tb]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        "\\scriptsize" if compact else "\\footnotesize",
        "\\setlength{\\tabcolsep}{5pt}",
        body.rstrip(),
    ]
    if note is not None:
        lines.append(f"\\par\\medskip\\raggedright\\scriptsize {note}")
    lines.append("\\end{table}")
    return "\n".join(lines) + "\n"


def write_table(frame: pd.DataFrame, directory: Path, name: str, **latex) -> list[Path]:
    """Write `frame` as `<name>.csv` to read and `<name>.tex` to `\\input`; see `to_latex`."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    csv_path, tex_path = directory / f"{name}.csv", directory / f"{name}.tex"
    csv_path.write_text(frame.to_csv())
    tex_path.write_text(to_latex(frame, label=f"tab:{name}", **latex))
    return [csv_path, tex_path]


# --- checking regenerated outputs ---------------------------------------------------

PIXEL_TOLERANCE = 2
"""Out of 255. matplotlib's drawing carries last-bit floating-point noise from one process
to the next, though every number drawn is bitwise stable; it moves antialiased edges by at
most 1/255. A real change to a figure moves pixels by far more, so figures are compared
by their PNG pixels within this tolerance, and tables byte for byte."""


def drifted(fresh_dir: Path, committed_dir: Path) -> list[str]:
    """What in `fresh_dir` disagrees with the file of the same name in `committed_dir`.

    Tables (`.csv`, `.tex`) must match byte for byte; figures by their PNG pixels within
    `PIXEL_TOLERANCE`, with the PDF beside them present.
    """
    problems = []
    for fresh in sorted(Path(fresh_dir).rglob("*")):
        if fresh.suffix not in (".csv", ".tex", ".png"):
            continue
        relative = fresh.relative_to(fresh_dir)
        committed = Path(committed_dir) / relative
        if not committed.exists():
            problems.append(f"{relative}: missing")
        elif fresh.suffix != ".png":
            if fresh.read_bytes() != committed.read_bytes():
                problems.append(f"{relative}: differs from a fresh generation")
        elif not committed.with_suffix(".pdf").exists():
            problems.append(f"{relative.with_suffix('.pdf')}: missing")
        else:
            new = np.asarray(Image.open(fresh).convert("RGB"), dtype=np.int16)
            old = np.asarray(Image.open(committed).convert("RGB"), dtype=np.int16)
            if new.shape != old.shape:
                problems.append(f"{relative}: {old.shape[:2]} committed, {new.shape[:2]} fresh")
            elif int(np.abs(new - old).max()) > PIXEL_TOLERANCE:
                problems.append(f"{relative}: pixels differ by up to {int(np.abs(new - old).max())}/255")
    return problems


# --- checksums --------------------------------------------------------------------
#
# Two files, both written by the build and compared by scripts/check.py:
# results/checksums.sha256 for what the build writes, and results/demos/runs.sha256 for
# the runs, which git does not carry. One `<sha256>  <path>` line per file, as `shasum`
# writes them.


def sha256(path: Path) -> str:
    """SHA-256 of one file, read in chunks so a 114 MB `params.csv` is not held in RAM."""
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1 << 20):
            hasher.update(chunk)
    return hasher.hexdigest()


def checksums(folder: Path, exclude: set[str] = frozenset()) -> dict[str, str]:
    """Every file under `folder` (path relative to it -> SHA-256), sorted. Hidden files
    (`.DS_Store`) and any whose name is in `exclude` are left out."""
    folder = Path(folder)
    found = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file() and not path.name.startswith(".") and path.name not in exclude:
            found[path.relative_to(folder).as_posix()] = sha256(path)
    return found


def write_checksums(path: Path, found: dict[str, str]) -> None:
    Path(path).write_text("".join(f"{digest}  {name}\n" for name, digest in found.items()))


def read_checksums(path: Path) -> dict[str, str]:
    recorded = {}
    for line in Path(path).read_text().splitlines():
        digest, _, name = line.partition("  ")
        recorded[name] = digest
    return recorded


def compare_checksums(recorded: dict[str, str], found: dict[str, str]) -> list[str]:
    """What differs between two sets of checksums, at most ten lines of each kind."""
    problems = []
    for label, names in (
        ("missing", sorted(set(recorded) - set(found))),
        ("not recorded", sorted(set(found) - set(recorded))),
        ("changed", sorted(n for n in set(recorded) & set(found) if recorded[n] != found[n])),
    ):
        problems += [f"{label}: {name}" for name in names[:10]]
        if len(names) > 10:
            problems.append(f"... and {len(names) - 10} more {label}")
    return problems
