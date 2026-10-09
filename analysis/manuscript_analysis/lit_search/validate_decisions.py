"""Check the hand-maintained decision files against their codebook.

Covers `screen-decisions.csv` in full, and the `Decision` column of `packages.csv`, which
shares the same vocabulary. The register was unguarded until 2026-09-21, and it showed: three
cells held off-vocabulary spellings (`Include - context (S1.5)`, `Exclude (borderline)`),
which made the register, the appendix's capsules-or-context list, and the count beneath it
disagree three ways. A one-line check would have caught it the day it was written.

The vocabularies are **read out of `decisions/screen-decisions-codebook.md`**, not duplicated
here, so the document a human consults and the rule a script enforces cannot drift apart.
Add a value to the codebook's bullet list and it becomes legal; that is the intended way to
extend the vocabulary.

The parse is deliberately dumb: under a known heading, every line of the form

    - `value` — prose

contributes `value`. Nothing else in the document is read.

Read-only. It never writes to `decisions/`.

    python3 src/validate_decisions.py            report problems, exit 0
    python3 src/validate_decisions.py --strict   exit non-zero if any problem is found
    python3 src/validate_decisions.py --quiet    print only problems

It warns rather than fails by default, and `run_all.py` calls it that way, because this is
the file a human is in the middle of editing: filling in a `decision` before its `reason` is
a normal intermediate state, not a broken repository, and `run_all.py` promises to be safe to
re-run at any time. `run_all.py --check` runs it `--strict`, which is where a problem should
stop the build.
"""
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

CODEBOOK = paths.DECISIONS / "screen-decisions-codebook.md"

# heading fragment -> the column it defines
SECTIONS = {
    "### `decision`": "decision",
    "### `status`": "status",
    "### `rule`": "rule",
}
# The `Out of scope:` classes live under their own paragraph inside the reason section.
SCOPE_MARKER = "**1. Out of scope.**"

BULLET = re.compile(r"^- `([^`]+)`")


def read_vocab():
    """Pull the controlled vocabularies out of the codebook."""
    if not CODEBOOK.exists():
        sys.exit(f"codebook not found: {CODEBOOK}")
    lines = CODEBOOK.read_text(encoding="utf-8").splitlines()

    vocab, scope, current = {k: [] for k in SECTIONS.values()}, [], None
    for line in lines:
        if line.startswith("#"):
            current = next((c for h, c in SECTIONS.items() if line.startswith(h)), None)
            continue
        if line.startswith(SCOPE_MARKER):
            current = "_scope"
            continue
        if line.startswith("**") and current == "_scope":
            current = None
            continue
        match = BULLET.match(line)
        if match and current == "_scope":
            scope.append(match.group(1))
        elif match and current:
            vocab[current].append(match.group(1))

    for column, values in vocab.items():
        if not values:
            sys.exit(f"codebook parse failed: no values found for {column!r}")
    if not scope:
        sys.exit("codebook parse failed: no 'Out of scope' classes found")
    return vocab, scope


def main():
    quiet = "--quiet" in sys.argv
    vocab, scope = read_vocab()
    rows = list(csv.DictReader(paths.SCREEN_DECISIONS.open(encoding="utf-8-sig")))

    problems = []

    # 1. Controlled columns carry only listed values.
    for column, allowed in vocab.items():
        seen = {}
        for i, row in enumerate(rows, start=2):
            value = row.get(column, "").strip()
            if value and value not in allowed:
                seen.setdefault(value, []).append(i)
        for value, where in sorted(seen.items()):
            rowlist = ", ".join(str(w) for w in where[:5])
            more = f" and {len(where) - 5} more" if len(where) > 5 else ""
            problems.append(
                f"{column}: {value!r} is not in the codebook "
                f"({len(where)} row(s): {rowlist}{more})")

    # 2. `Out of scope:` reasons name a listed class.
    for i, row in enumerate(rows, start=2):
        reason = row.get("reason", "").strip()
        if reason.startswith("Out of scope:"):
            cls = reason[len("Out of scope:"):].strip()
            if cls not in scope:
                problems.append(f"reason (row {i}): out-of-scope class {cls!r} is not listed")

    # 3. A reason that cites the evidence must still agree with it.
    #
    # `known` is recomputed from `data/` on every run; `reason` is frozen the moment a human
    # writes it. So a reason of the form "mentions known package: X" can outlive the match
    # that justified it, and nothing else would notice. That is not hypothetical: the first
    # pass matched bare `surveillance` and bare `dust`, the lexicon was later tightened to
    # `\bsurveillance package\b`, and 50 exclusions were left resting on evidence the
    # pipeline no longer reproduces.
    tag = "mentions known package:"
    for i, row in enumerate(rows, start=2):
        reason = row.get("reason", "")
        if tag not in reason:
            continue
        known = row.get("known", "").strip()
        if not known:
            problems.append(
                f"row {i}: reason cites a package mention, but `known` is empty - the "
                f"lexicon no longer reproduces it ({reason.split(tag)[1].strip()!r})")
            continue
        cited = {n.strip() for n in reason.split(tag)[1].strip().split(";")}
        matched = {n.strip() for n in known.split(";")}
        if not cited & matched:
            problems.append(
                f"row {i}: reason cites {sorted(cited)} but `known` has {sorted(matched)}")

    # 4. decision and reason travel together.
    for i, row in enumerate(rows, start=2):
        has_d = bool(row.get("decision", "").strip())
        has_r = bool(row.get("reason", "").strip())
        if has_d != has_r:
            missing = "reason" if has_d else "decision"
            problems.append(f"row {i}: has a {'decision' if has_d else 'reason'} "
                            f"but no {missing}")

    # The register shares the decision vocabulary, so hold it to the same list.
    register = list(csv.DictReader(paths.PACKAGES.open(encoding="utf-8-sig")))
    seen = {}
    for i, row in enumerate(register, start=2):
        value = row.get("Decision", "").strip()
        if value and value not in vocab["decision"]:
            seen.setdefault(value, []).append(i)
    for value, where in sorted(seen.items()):
        problems.append(
            f"packages.csv Decision: {value!r} is not in the codebook "
            f"({len(where)} row(s): {', '.join(str(w) for w in where[:5])})")

    done = sum(1 for r in rows if r.get("decision", "").strip())
    if not quiet:
        print(f"screen-decisions.csv: {len(rows)} rows, {len(vocab['decision'])} decisions / "
              f"{len(vocab['status'])} statuses / {len(vocab['rule'])} rules / "
              f"{len(scope)} out-of-scope classes in the codebook")
        print(f"  register: {len(register)} packages, Decision column checked")
        print(f"  dispositions: {done}/{len(rows)}"
              + ("  - complete" if done == len(rows) else
                 f" - {len(rows) - done} still blank"))

    if problems:
        print(f"  {len(problems)} problem(s):")
        for p in problems:
            print(f"    {p}")
        # Deprecated-but-documented values are listed in the codebook, so anything that
        # reaches here is genuinely unlisted.
        if "--strict" in sys.argv:
            sys.exit(1)
    elif not quiet:
        print("  vocabulary: clean")


if __name__ == "__main__":
    main()
