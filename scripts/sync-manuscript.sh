#!/usr/bin/env bash
#
# Mirror the manuscript from the Overleaf clone into this repository.
#
#   scripts/sync-manuscript.sh            report what differs; change nothing
#   scripts/sync-manuscript.sh --apply    copy Overleaf's version over this one
#
# The direction is deliberately one-way. `epymorph_ms_overleaf` is the clone that
# round-trips with the Overleaf editor, so it is where edits actually happen; this
# repository holds a mirror so that the manuscript and the analysis that feeds it live
# together. Editing `manuscript/` here and then running --apply would silently discard that
# edit, so the report below flags which side is newer before you commit to anything.
#
# Only content is synced. The Springer template files (sn-jnl.cls, sn-*.bst) and Overleaf's
# own scaffolding (sn-article.tex, user-manual.pdf, sample figures) are left alone: they are
# static, and this repository deliberately does not carry all of them.
set -euo pipefail

OVERLEAF="${OVERLEAF:-$HOME/Documents/Claude/Projects/epymorph_ms_overleaf}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$HERE/manuscript"

APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

[[ -d "$OVERLEAF" ]] || { echo "no Overleaf clone at $OVERLEAF (set \$OVERLEAF)" >&2; exit 1; }

# Content files, relative to each manuscript root.
# Built with a read loop rather than `mapfile`, which is bash 4+; macOS ships bash 3.2.
PATHS=()
while IFS= read -r rel; do PATHS+=("$rel"); done < <(
  cd "$OVERLEAF" && ls main.tex references.bib sections/*.tex supplementary/*.tex 2>/dev/null
)

differing=0
newer_here=0
for rel in "${PATHS[@]}"; do
  src="$OVERLEAF/$rel"
  dst="$DEST/$rel"
  if [[ ! -f "$dst" ]]; then
    echo "  NEW      $rel"
    differing=$((differing + 1))
    continue
  fi
  if ! cmp -s "$src" "$dst"; then
    differing=$((differing + 1))
    if [[ "$dst" -nt "$src" ]]; then
      echo "  DIFFERS  $rel   <-- this repo's copy is NEWER; check before overwriting"
      newer_here=$((newer_here + 1))
    else
      echo "  DIFFERS  $rel"
    fi
  fi
done

if [[ $differing -eq 0 ]]; then
  echo "manuscript: in sync (${#PATHS[@]} files identical)"
  exit 0
fi

echo "manuscript: $differing of ${#PATHS[@]} files differ"

if [[ $APPLY -eq 0 ]]; then
  echo "run with --apply to copy Overleaf's version over this repository's"
  exit 0
fi

if [[ $newer_here -gt 0 ]]; then
  echo
  echo "REFUSING: $newer_here file(s) are newer here than in Overleaf." >&2
  echo "That usually means the edit was made in the wrong copy. Reconcile by hand, or" >&2
  echo "touch the Overleaf file once you are sure its version is the one you want." >&2
  exit 1
fi

for rel in "${PATHS[@]}"; do
  mkdir -p "$DEST/$(dirname "$rel")"
  cp "$OVERLEAF/$rel" "$DEST/$rel"
done
echo "copied ${#PATHS[@]} files into manuscript/"

# Prove it, rather than assume it.
for rel in "${PATHS[@]}"; do
  cmp -s "$OVERLEAF/$rel" "$DEST/$rel" || { echo "VERIFY FAILED: $rel" >&2; exit 1; }
done
echo "verified: every synced file is byte-identical"
echo
echo "next: review with 'git -C \"$HERE\" diff manuscript/' before committing"
