#!/usr/bin/env bash
# Regenerate the demos' run outputs: every model, both ensemble seeds.
#
# This is the expensive half of the analysis, roughly 8-10 hours wall clock on one
# machine. It writes ~1 GB into results/demos/runs/, which git does not carry. A run
# folder produced under the SAME configuration is skipped, so re-running this script
# after an interruption resumes rather than starts over.
#
# A fixed seed reproduces an ensemble byte for byte on the same platform (verified
# 2026-09-22). On a different platform expect the scores to agree and the bytes not to;
# compare results/demos/tables/ rather than the ensembles.
#
# Usage:  scripts/run-demos.sh [--seeds "0 1"] [--jobs N]
set -euo pipefail

SEEDS="0 1"
JOBS=3
while [ $# -gt 0 ]; do
  case "$1" in
    --seeds) SEEDS="$2"; shift 2 ;;
    --jobs)  JOBS="$2";  shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

cd "$(dirname "$0")/.."
export PYTHONPATH="analysis/src${PYTHONPATH:+:$PYTHONPATH}"

FLU_MODELS=(
  "models.multi_strata_flu:empirical"
  "models.multi_strata_flu:homogeneous"
  "models.single_strata"
)
COVID_MODELS=(
  "models.spatial_movement:movement"
  "models.spatial_movement:county"
  "models.state_aggregate:model"
)

run_group() {          # run_group <demo> <realizations> <seed> <model>...
  local demo=$1 realizations=$2 seed=$3; shift 3
  local pids=()
  for spec in "$@"; do
    echo "  [$demo seed $seed] $spec"
    python -m "manuscript_analysis.demos.${demo}.run_season" \
      "$spec" -n "$realizations" --seed "$seed" &
    pids+=($!)
    # Each fit is single-threaded, so run up to $JOBS of them at once. Polls rather than
    # `wait -n`, which needs bash 4.3 and macOS ships bash 3.2.
    while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do sleep 10; done
  done
  for pid in "${pids[@]}"; do wait "$pid"; done
}

for seed in $SEEDS; do
  echo "== influenza, seed $seed (R=300) =="
  run_group flu 300 "$seed" "${FLU_MODELS[@]}"
  echo "== covid, seed $seed (R=600) =="
  run_group covid 600 "$seed" "${COVID_MODELS[@]}"
done

echo
echo "done. Next: scripts/build-figures.sh"
