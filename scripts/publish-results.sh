#!/usr/bin/env bash
#
# Publish generated figures, tables and numbers into the Overleaf clone.
#
#   scripts/publish-results.sh            report what would change; change nothing
#   scripts/publish-results.sh --apply    copy them over, then verify byte-equality
#
# The mirror image of sync-manuscript.sh, and deliberately the opposite direction.
# Together the two scripts are NOT a bidirectional sync, which would need merging; they
# are two one-way mirrors over **disjoint sets of files**:
#
#   prose        main.tex, sections/, supplementary/, references.bib
#                written by a human in Overleaf      ->  sync-manuscript.sh  ->  here
#
#   generated    figures/, tables/, manuscript-numbers.tex
#                written only by this repository's scripts  ->  this script  ->  Overleaf
#
# No file is ever written by both sides, so neither script can lose an edit the other
# made. That is the whole reason the split is safe.
#
# PDFs rather than PNGs: the PNGs in results/figures/ are for looking at, the PDFs are
# vector and are what LaTeX should include.
set -euo pipefail

OVERLEAF="${OVERLEAF:-$HOME/Documents/Claude/Projects/epymorph_ms_overleaf}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

[[ -d "$OVERLEAF" ]] || { echo "no Overleaf clone at $OVERLEAF (set \$OVERLEAF)" >&2; exit 1; }

# "<source, relative to this repo>  <destination, relative to the Overleaf root>"
# Built with a read loop rather than `mapfile`, which is bash 4+; macOS ships bash 3.2.
PAIRS=()
# Returns 0 even when the file is absent: `manuscript-numbers.tex` does not exist yet,
# and under `set -e` a failing test as the last command would end the script silently.
add_pair() {
  if [[ -f "$HERE/$1" ]]; then PAIRS+=("$1|$2"); fi
  return 0
}

while IFS= read -r f; do
  add_pair "results/figures/$f" "figures/$f"
done < <(cd "$HERE/results/figures" 2>/dev/null && ls ./*.pdf 2>/dev/null | sed 's|^\./||')

while IFS= read -r f; do
  add_pair "results/demos/tables/$f" "tables/$f"
done < <(cd "$HERE/results/demos/tables" 2>/dev/null && ls ./*.tex 2>/dev/null | sed 's|^\./||')

add_pair "results/lit-search/table-1-maintext.tex" "tables/table-1-maintext.tex"
add_pair "results/manuscript-numbers.tex" "manuscript-numbers.tex"

if [[ ${#PAIRS[@]} -eq 0 ]]; then
  echo "nothing generated yet. Run scripts/build-figures.sh first." >&2
  exit 1
fi

changed=0
edited=0
for pair in "${PAIRS[@]}"; do
  rel_src="${pair%%|*}"
  rel_dst="${pair##*|}"
  src="$HERE/$rel_src"
  dst="$OVERLEAF/$rel_dst"

  if [[ ! -f "$dst" ]]; then
    echo "  NEW       $rel_dst"
    changed=$((changed + 1))
    continue
  fi
  if cmp -s "$src" "$dst"; then
    continue
  fi
  changed=$((changed + 1))

  # A generated .tex carries a "do not hand-edit" header. If Overleaf's copy has lost it,
  # someone pasted over the file there, and overwriting it would discard their work
  # without either script being able to tell. Worth naming out loud.
  if [[ "$rel_dst" == *.tex ]] && ! head -1 "$dst" | grep -q '^% GENERATED'; then
    echo "  EDITED?   $rel_dst  (no GENERATED header in Overleaf's copy)"
    edited=$((edited + 1))
  else
    echo "  update    $rel_dst"
  fi
done

echo
if [[ $changed -eq 0 ]]; then
  echo "Overleaf is up to date: ${#PAIRS[@]} generated files, all identical."
  exit 0
fi

if [[ $edited -gt 0 ]]; then
  echo "$edited file(s) in Overleaf look hand-edited. Look at them before applying:"
  echo "  a generated table is rebuilt from the analysis, so an edit made there is lost."
fi

if [[ $APPLY -eq 0 ]]; then
  echo "$changed file(s) would change. Re-run with --apply to copy them."
  exit 0
fi

for pair in "${PAIRS[@]}"; do
  rel_src="${pair%%|*}"
  rel_dst="${pair##*|}"
  mkdir -p "$(dirname "$OVERLEAF/$rel_dst")"
  cp "$HERE/$rel_src" "$OVERLEAF/$rel_dst"
done

# Verify rather than trust the copy.
for pair in "${PAIRS[@]}"; do
  rel_src="${pair%%|*}"
  rel_dst="${pair##*|}"
  cmp -s "$HERE/$rel_src" "$OVERLEAF/$rel_dst" || {
    echo "VERIFY FAILED: $rel_dst" >&2
    exit 1
  }
done

echo "copied and verified ${#PAIRS[@]} files into $OVERLEAF"
echo
echo "Next, in the Overleaf clone: git add -A && git commit && git push,"
echo "then click Pull in Overleaf's GitHub panel."
