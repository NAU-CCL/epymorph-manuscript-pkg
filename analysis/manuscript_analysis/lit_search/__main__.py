"""Run the software-landscape search on its own.

    python -m manuscript_analysis.lit_search            screen, audit, register, counts
    python -m manuscript_analysis.lit_search --check    also check the manuscript

`just build` and `just check` run it as their first step.
"""
import sys

from manuscript_analysis import lit_search

lit_search.run(check="--check" in sys.argv)
