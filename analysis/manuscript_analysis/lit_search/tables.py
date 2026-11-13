"""Verify the comparison worksheet's citations against the bibliography.

The worksheet (`decisions/table-marks.csv`) names a `bib_key` and a `doi` for each package,
and those are what the manuscript cites. This checks that every key resolves in the
bibliography and that the DOI beside it is the one the bibliography holds, so a citation
cannot quietly point at the wrong work. Exits non-zero on a mismatch. (That Table 1 agrees
with the same worksheet is `table1_tex.py`'s check.)
"""
import re
import sys

from . import paths


def parse_bib(path):
    """A minimal BibTeX reader: enough for a Zotero export, no dependency."""
    text = open(path, encoding="utf-8", errors="replace").read()
    entries = []
    for match in re.finditer(r"@(\w+)\s*\{\s*([^,]+),", text):
        start, i, depth = match.end(), text.index("{", match.start()) + 1, 1
        while i < len(text) and depth:
            depth += (text[i] == "{") - (text[i] == "}")
            i += 1
        entry = {"type": match.group(1), "key": match.group(2).strip()}
        for field in re.finditer(
            r"(\w+)\s*=\s*\{(.*?)\}\s*,?\s*(?=\n\t\w+\s*=|\n\}|$)",
            text[start:i], re.S,
        ):
            entry[field.group(1).lower()] = re.sub(r"[{}]", "", field.group(2)).strip()
        entries.append(entry)
    return entries


def main():
    rows = paths.read_rows(paths.TABLE_MARKS)
    by_key = {e["key"]: e for e in parse_bib(paths.BIB)}

    problems, checked, no_key = [], 0, []
    for row in rows:
        package = row["package"]
        key, doi = row["bib_key"].strip(), row["doi"].strip()
        if not key:
            # epymorph is this manuscript, so it has no citation of its own.
            no_key.append(package)
            if doi:
                problems.append(f"{package}: records a DOI but no bib_key")
            continue
        entry = by_key.get(key)
        if entry is None:
            problems.append(f"{package}: bib_key {key!r} is not in {paths.BIB.name}")
            continue
        recorded = entry.get("doi", "").strip()
        if doi and recorded and doi.lower() != recorded.lower():
            problems.append(
                f"{package}: worksheet DOI {doi!r}, but {key!r} holds {recorded!r}")
            continue
        checked += 1

    print(f"worksheet citations: {checked}/{len(rows)} packages verified against "
          f"{paths.BIB.name}")
    if no_key:
        print(f"  no citation by design: {', '.join(no_key)}")
    if problems:
        print(f"  {len(problems)} problem(s):")
        for item in problems:
            print(f"    {item}")
        sys.exit(1)
