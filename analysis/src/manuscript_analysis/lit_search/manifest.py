"""Checksum `data/` and `results/` into `results/MANIFEST.sha256`.

`data/` is the evidence and cannot be re-fetched: the same Lens query that returned 1,009
records in July 2026 returns more every month, so the archived exports are the only copy of
what Appendix S1's numbers were computed from. If a byte in one of them changes, every count
in the appendix changes with it and nothing else would say so.

So the manifest is written on every run, and **the `data/` half is compared against the
previous manifest first**. A regenerated checksum that nobody compares is ceremony; the
comparison is the part that does the work. `results/` is regenerable, so its entries are
recorded rather than policed.

Verify independently at any time, from the `software-lit-search` directory:

    shasum -a 256 -c results/MANIFEST.sha256

(`shasum` is the macOS tool; on Linux it is usually `sha256sum -c`.)
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

MANIFEST = paths.RESULTS / "MANIFEST.sha256"


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def entries():
    """(relative path, digest) for every file in data/ and results/, sorted."""
    out = []
    for root in (paths.DATA, paths.RESULTS):
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path == MANIFEST or path.name == ".DS_Store":
                continue
            out.append((path.relative_to(paths.ROOT).as_posix(), digest(path)))
    return out


def previous():
    """The data/ entries of the manifest as it stands, before we overwrite it."""
    if not MANIFEST.exists():
        return {}
    old = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if "  " not in line:
            continue
        sha, name = line.split("  ", 1)
        if name.startswith("data/"):
            old[name] = sha
    return old


def main():
    before = previous()
    rows = entries()
    paths.RESULTS.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text("".join(f"{sha}  {name}\n" for name, sha in rows), encoding="utf-8")

    now = {name: sha for name, sha in rows if name.startswith("data/")}
    print(f"wrote {MANIFEST.relative_to(paths.ROOT)}: {len(rows)} files "
          f"({len(now)} in data/, {len(rows) - len(now)} in results/)")

    if not before:
        print("  data/: no previous manifest to compare against; this run establishes it")
        return
    changed = sorted(n for n in now if n in before and now[n] != before[n])
    added = sorted(set(now) - set(before))
    gone = sorted(set(before) - set(now))
    if changed or gone:
        print("  data/ HAS CHANGED SINCE THE LAST RUN. The archived exports are the evidence "
              "for every number in Appendix S1; they should never change.")
        for name in changed:
            print(f"    modified: {name}")
        for name in gone:
            print(f"    missing:  {name}")
        sys.exit(1)
    if added:
        for name in added:
            print(f"  data/: new file recorded: {name}")
    else:
        print("  data/: unchanged since the last run")


if __name__ == "__main__":
    main()
