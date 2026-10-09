#!/usr/bin/env bash
#
# Build Word copies of the manuscript and supplement, for collaborators who comment in Word.
#
#   scripts/build-docx.sh
#
# Reads the Overleaf clone (what collaborators see in Overleaf), repairs what pandoc cannot
# convert on its own, and writes
#
#   results/manuscript-docx/epymorph-ms_main_<date>.docx
#   results/manuscript-docx/epymorph-ms_supplement_<date>.docx
#
# ready to copy into a Team or OneDrive folder. Each file records the Overleaf commit it
# was built from in its document properties (File > Properties in Word). The Word copy is
# one-way: comments come back to Overleaf by
# hand, never by importing the .docx. The repairs, and why each is needed, are in
# analysis/manuscript_analysis/build_docx.py.
#
# Needs pandoc (3.x). Pull the Overleaf clone first, so the copy is current.
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="analysis${PYTHONPATH:+:$PYTHONPATH}"

command -v pandoc >/dev/null || { echo "pandoc not found; install it first" >&2; exit 1; }

python -m manuscript_analysis.build_docx
