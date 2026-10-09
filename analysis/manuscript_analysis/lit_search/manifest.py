"""Checksum the archived search exports into `results/lit-search/MANIFEST.sha256`.

`data/lit-search/raw/` is the evidence and cannot be re-fetched: the same Lens query that
returned 1,009 records in July 2026 returns more every month, so the archived exports are
the only copy of what Appendix S1's numbers were computed from. If a byte in one of them
changes, every count in the appendix changes with it and nothing else would say so.

So **the new checksums are compared against the previous manifest first**; if they differ,
the run fails and the manifest is left as it was, so the failure repeats until someone
looks. A regenerated checksum that nobody compares is ceremony; the comparison is the part
that does the work. (The pipeline's outputs are checksummed with the rest of the build's,
in `results/checksums.sha256`.)

Verify independently at any time, from the repository root:

    shasum -a 256 -c results/lit-search/MANIFEST.sha256

(`shasum` is the macOS tool; on Linux it is usually `sha256sum -c`.)
"""
import sys

from .. import util
from . import paths

MANIFEST = paths.RESULTS / "MANIFEST.sha256"


def main():
    prefix = paths.DATA.relative_to(paths.ROOT).as_posix()
    now = {}
    for name, digest in util.checksums(paths.DATA).items():
        now[f"{prefix}/{name}"] = digest

    before = {}
    if MANIFEST.exists():
        for name, digest in util.read_checksums(MANIFEST).items():
            if name.startswith(prefix):
                before[name] = digest

    # Compare BEFORE writing. Writing first would record the changed exports as the new
    # baseline, so the run that noticed a change would fail and every run after it pass.
    if before:
        changed = sorted(n for n in now if n in before and now[n] != before[n])
        gone = sorted(set(before) - set(now))
        if changed or gone:
            print("  data/ HAS CHANGED SINCE THE LAST RUN. The archived exports are the "
                  "evidence for every number in Appendix S1; they should never change.")
            for name in changed:
                print(f"    modified: {name}")
            for name in gone:
                print(f"    missing:  {name}")
            print(f"  {MANIFEST.relative_to(paths.ROOT)} was left as it was.")
            sys.exit(1)

    util.write_checksums(MANIFEST, now)
    print(f"wrote {MANIFEST.relative_to(paths.ROOT)}: {len(now)} archived exports")

    if not before:
        print("  data/: no previous manifest to compare against; this run establishes it")
        return
    added = sorted(set(now) - set(before))
    if added:
        for name in added:
            print(f"  data/: new file recorded: {name}")
    else:
        print("  data/: unchanged since the last run")
