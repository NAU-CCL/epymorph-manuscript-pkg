#!/usr/bin/env bash
# Every check this repository makes of itself. Exits non-zero on the first failure.
#
# All three checks are self-contained: each regenerates something and compares it with
# what is committed, so a file that stopped agreeing with the code that produces it is
# named rather than quietly shipped.
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="analysis/src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONHASHSEED=0  # as in build-figures.sh

echo "== generated files =="
# Every .tex under results/ is written by code and says so on its first line. Checked
# before anything regenerates, so a hand-edit that removed the header is caught rather
# than silently overwritten.
unmarked=$(find results -name '*.tex' -exec sh -c \
  'head -1 "$1" | grep -q "^% GENERATED" || echo "$1"' _ {} \;)
if [ -n "$unmarked" ]; then
  echo "  no % GENERATED header (hand-written, or hand-edited?):"
  echo "$unmarked" | sed 's/^/    /'
  exit 1
fi
echo "  every .tex under results/ carries its % GENERATED header"

echo
echo "== the software-landscape pipeline =="
python -m manuscript_analysis.lit_search --check

# The rest need the ensembles, which git does not carry.
if [ -d results/demos/runs ]; then
  echo
  echo "== the demos =="
  # Each demo's figures and tables come from its notebook, rerun into a scratch folder.
  # It refits only its walkthrough model, and stops rather than fit if a run is missing.
  for demo in demo-flu demo-covid; do
    printf '  %-44s' "$demo.ipynb agrees with a fresh run"
    scratch=$(mktemp -d)
    if ! python -m papermill "analysis/src/manuscript_analysis/$demo.ipynb" \
        "$scratch/$demo.ipynb" --cwd analysis/src/manuscript_analysis \
        -p output_dir "$scratch" -p fit_missing_runs False > "$scratch/papermill.log" 2>&1; then
      echo "FAILED"; tail -20 "$scratch/papermill.log"; exit 1
    fi
    python - "$scratch" <<'PYTHON'
import sys
from manuscript_analysis.util import drifted
problems = drifted(sys.argv[1], "results/demos")
if problems:
    print("drifted:", *problems, sep="\n    ")
    sys.exit(1)
print("OK")
PYTHON
    rm -rf "$scratch"
  done
  printf '  %-44s' "run outputs match MANIFEST.sha256"
  python -m manuscript_analysis.demos.manifest --check >/dev/null && echo OK
else
  echo
  echo "results/demos/runs/ absent: skipping the demo checks."
  echo "Run scripts/run-demos.sh, or fetch the archive; see results/demos/README.md."
fi

echo
echo "all checks passed"
