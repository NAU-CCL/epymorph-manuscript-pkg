#!/usr/bin/env bash
# Regenerate the demos' runs, then their figures and tables: each demo is one notebook.
#
# This is the expensive half of the analysis, about 5 hours on one machine without the
# archived runs (Demo 1's two stratified models take about four hours each, four runs at a
# time). It writes ~1 GB into results/demos/runs/, which git does not carry. A run already
# on disk with the same settings is reused, so re-running this after an interruption
# resumes rather than starts over.
#
# A fixed seed reproduces a run byte for byte on the same platform (verified 2026-10-08,
# in parallel workers). On a different platform expect the scores to agree and the bytes
# not to; compare results/demos/tables/ rather than the runs.
#
# The executed notebooks, outputs and all, are written to results/demos/notebook/.
#
# Usage:  scripts/run-demos.sh
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="analysis/src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONHASHSEED=0  # as in build-figures.sh

for demo in demo-flu demo-covid; do
  echo "== $demo =="
  python -m papermill "analysis/src/manuscript_analysis/$demo.ipynb" \
    "results/demos/notebook/$demo.ipynb" --cwd analysis/src/manuscript_analysis \
    -p output_dir "$PWD/results/demos"
done

echo
echo "done: the runs, figures and tables are written."
