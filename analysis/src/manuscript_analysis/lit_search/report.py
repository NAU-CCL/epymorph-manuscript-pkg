"""
Write every number Appendix S1 quotes to one machine-readable file, and check the prose.

The appendix states about twenty counts across §S1.9 and §S1.10. Each one was, until now,
a number somebody read off a terminal and typed into a draft. `counts.json` makes them an
output of the pipeline, and `--check` reads them back out of the appendix and asserts they
still match, which is the guarantee actually wanted. The Methods summary of the search
quotes the headline counts too, and is checked the same way.

Same idea as the `\\newcommand` macro file planned for the demo figures: the paper and the
analysis cannot disagree, because one generates the other's numbers.

    python3 src/report.py            write results/counts.json and lexicon-prose.txt
    python3 src/report.py --check    additionally check them against the appendix
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths
import recall
import screen
from lexicon import BLOCKS


# Terms whose pattern is a stem or whose prose form is capitalised. Everything not listed
# passes through as written, so this stays short and only records real exceptions.
DISPLAY = {
    "uncertainty quantif": "uncertainty quantification", "emulat": "emulation",
    "calibrat": "calibration", "github": "GitHub", "cran": "CRAN", "pypi": "PyPI",
    "r package": "R package", "python package": "Python package", "julia": "Julia",
    "smc": "SMC", "mcmc": "MCMC", "pmcmc": "pMCMC", "abc smc": "ABC-SMC",
    "sequential monte carlo": "sequential Monte Carlo", "ensemble kalman": "ensemble Kalman",
    "kalman filter": "Kalman filter", "bayesian": "Bayesian",
    "markov chain monte carlo": "Markov chain Monte Carlo",
    "approximate bayesian": "approximate Bayesian",
    "hamiltonian monte carlo": "Hamiltonian Monte Carlo", "state space": "state-space",
    "seir": "SEIR", "sir model": "SIR model", "covid": "COVID", "ebola": "Ebola",
    "mpox": "mpox", "open source": "open-source",
}


def pretty(pattern):
    """Turn a lexicon regex back into the human term it stands for."""
    term = pattern.replace(r"\b", "").replace("[- ]", " ")
    term = re.sub(r"\(([^)]*)\)", lambda m: "/".join(m.group(1).split("|")), term)
    term = term.replace("?", "").strip()
    return DISPLAY.get(term, term)


def write_lexicon_prose():
    """The §S1.1 term listing, generated so the protocol and the screen cannot drift."""
    lines = []
    for name, patterns in BLOCKS.items():
        lines.append(f"{name}:")
        lines.append("  " + ", ".join(pretty(p) for p in patterns))
        lines.append("")
    paths.LEXICON_PROSE.write_text("\n".join(lines), encoding="utf-8")
    return len(BLOCKS)


# Terms the appendix lists in a condensed form. Declared rather than silently tolerated, so
# that a genuine omission is not mistaken for a house-style contraction.
CONDENSED = {
    "available from": "available at/from",
    "meta-population": "metapopulation",
}


def check_lexicon_listing():
    """Assert S1.1 lists every term the screen actually runs on.

    The paragraph is prose, deliberately: a mechanically dumped term list reads worse than a
    written one. What has to be true is not that the text is generated but that it is
    *complete*, and that is what this checks, in both directions.
    """
    if not paths.APPENDIX.exists():
        print("  lexicon listing: SKIPPED, no appendix at "
              f"{paths.APPENDIX}")
        return 0
    text = paths.APPENDIX.read_text(encoding="utf-8")
    found = re.search(r"co-occurrence of three term sets:(.*?)"
                      r"Records matching all", text, re.S)
    if not found:
        sys.exit("S1's pre-filter paragraph could not be located in the appendix")
    para = re.sub(r"\s+", " ", found.group(1)).lower()

    missing = []
    for name, patterns in BLOCKS.items():
        for pattern in patterns:
            term = pretty(pattern)
            if term.lower() in para:
                continue
            condensed = CONDENSED.get(term.lower())
            if condensed and condensed.lower() in para:
                continue
            missing.append(f"{name}: {term!r}")
    if missing:
        print(f"  lexicon listing: {len(missing)} term(s) screened on but not listed in S1:")
        for item in missing:
            print(f"    {item}")
        return len(missing)
    total = sum(len(v) for v in BLOCKS.values())
    print(f"  lexicon listing: all {total} screened terms are listed in S1")
    return 0


# Every count the manuscript quotes, as (count, phrase that carries it). The regex pulls the
# number out of the live draft so a drifted figure is caught rather than assumed. A count may
# be quoted more than once (in prose and in a table), so this is a list, not a dict. Each
# pattern anchors on the few words next to the number, so that copy-editing the sentence
# around it does not break the check.
APPENDIX_CLAIMS = [
    ("pubmed_retrieved",   r"PubMed search returned \\textbf\{([\d,]+) records\}"),
    ("pubmed_screened",    r"\\textbf\{([\d,]+)\} included abstracts"),
    ("pubmed_advanced",    r"pre-filter advanced \\textbf\{([\d,]+) records\}"),
    ("lens_retrieved",     r"Lens\.org export returned \\textbf\{([\d,]+) records\}"),
    ("lens_duplicates",    r"([\d,]+) were duplicates with PubMed"),
    ("lens_advanced",      r"keyword filter led to \\textbf\{([\d,]+)\}"),
    ("pubmed_dropped",     r"The ([\d,]+) PubMed and [\d,]+ Lens\.org records"),
    ("lens_dropped",       r"PubMed and ([\d,]+) Lens\.org records"),
    ("titlesweep",         r"\(\\textbf\{([\d,]+)\} records\); all were out of scope"),
    ("random_sample",      r"random sample of \\textbf\{([\d,]+)\}"),
    ("random_sample_seed", r"seed\s*\$?=\s*([\d,]+)"),
    # the sources table
    ("pubmed_retrieved",   r"([\d,]+) records retrieved, [\d,]+ with abstracts screened"),
    ("pubmed_screened",    r"records retrieved, ([\d,]+) with abstracts screened"),
    ("lens_retrieved",     r"([\d,]+) records retrieved \(journal, conference"),
]


# The Methods summary quotes the headline counts.
METHODS_CLAIMS = [
    ("total_screened",     r"yielded ([\d,]+) unique records with abstracts"),
    ("total_advanced",     r"led to ([\d,]+) records for manual screening"),
]


def check_claims(path, claims, counts):
    """Pull each claimed count out of one manuscript file and compare it with the pipeline."""
    # Flattened, because LaTeX hard-wraps prose: a claim can sit across a line break and the
    # pattern should not have to know where the wrap happens to fall.
    text = re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))
    ok, bad, unfound = 0, [], []
    for key, pattern in claims:
        match = re.search(pattern, text)
        if not match:
            unfound.append(key)
            continue
        stated = int(match.group(1).replace(",", ""))
        if stated == counts[key]:
            ok += 1
        else:
            bad.append((key, stated, counts[key]))

    print(f"\nmanuscript check ({path.name}):")
    print(f"  {ok} of {len(claims)} counts match the pipeline")
    for key, stated, actual in bad:
        print(f"  MISMATCH {key}: {path.name} says {stated:,}, pipeline says {actual:,}")
    for key in unfound:
        print(f"  NOT FOUND {key}: the phrase this looks for is not in the draft")
    return not bad and not unfound


def main():
    counts = screen.main()
    print()
    counts.update(recall.main())
    blocks = write_lexicon_prose()

    paths.COUNTS.write_text(json.dumps(counts, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    print(f"\nwrote {paths.COUNTS.name} ({len(counts)} values) "
          f"and {paths.LEXICON_PROSE.name} ({blocks} blocks)")

    if "--check" in sys.argv:
        ok = check_claims(paths.APPENDIX, APPENDIX_CLAIMS, counts)
        if not check_claims(paths.METHODS_SURVEY, METHODS_CLAIMS, counts):
            ok = False
        if check_lexicon_listing():
            ok = False
        # Every advanced record carries a hand-entered decision. (That each decision has a
        # reason, and the reverse, is `validate_decisions.py --strict`'s check.)
        blank = counts["total_advanced"] - counts["advanced_dispositioned"]
        if blank:
            print(f"  INCOMPLETE: {blank} of {counts['total_advanced']} advanced records "
                  f"have no decision in {paths.SCREEN_DECISIONS.name}")
            ok = False
        if not ok:
            sys.exit(1)


if __name__ == "__main__":
    main()
