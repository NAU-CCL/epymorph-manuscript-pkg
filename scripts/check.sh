#!/usr/bin/env bash
# Every check this repository makes of itself. Exits non-zero on the first failure.
#
# All three checks are self-contained: each regenerates something and compares it with
# what is committed, so a file that stopped agreeing with the code that produces it is
# named rather than quietly shipped.
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="analysis/src${PYTHONPATH:+:$PYTHONPATH}"

echo "== the software-landscape pipeline =="
python -m manuscript_analysis.lit_search --check

# The rest need the ensembles, which git does not carry.
if [ -d results/demos/runs ]; then
  echo
  echo "== the demos =="
  printf '  %-44s' "tables agree with a fresh generation"
  python -m manuscript_analysis.demos.tables --check >/dev/null && echo OK
  printf '  %-44s' "run outputs match MANIFEST.sha256"
  python -m manuscript_analysis.demos.manifest --check >/dev/null && echo OK
else
  echo
  echo "results/demos/runs/ absent: skipping the demo checks."
  echo "Run scripts/run-demos.sh, or fetch the archive; see results/demos/README.md."
fi

echo
echo "all checks passed"
