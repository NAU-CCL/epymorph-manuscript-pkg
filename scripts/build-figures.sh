#!/usr/bin/env bash
# Build every figure and table the manuscript uses, from the run outputs.
#
# Seconds, not hours: everything expensive already happened in scripts/run-demos.sh.
# Writes results/demos/{figures,tables}/, both of which are safe to delete.
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="analysis/src${PYTHONPATH:+:$PYTHONPATH}"
# The PDFs embed a subset of each font, and matplotlib orders its glyphs by Python's string
# hashing, which is randomised per process unless pinned. Pinning it keeps a rebuilt PDF
# from changing in git when its drawing has not. (Last-bit floating-point noise in the
# drawing can still move a coordinate's tenth decimal; check.sh compares pixels, not bytes.)
export PYTHONHASHSEED=0

if [ ! -d results/demos/runs ]; then
  echo "results/demos/runs/ is missing: run scripts/run-demos.sh first," >&2
  echo "or fetch the archived outputs. See results/demos/README.md." >&2
  exit 1
fi

python -m manuscript_analysis.demos.export
python -m manuscript_analysis.demos.tables
