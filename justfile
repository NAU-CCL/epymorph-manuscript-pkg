# https://just.systems. Run `just` for the list. Every recipe runs from the repository root.

# A Census key in .env reaches epymorph this way. Builds do not need one: every Census
# input is frozen in data/raw/. Only refreshing an input does.
set dotenv-load

# List the recipes.
default:
    @just --list --unsorted

# Install the pinned environment, and make a .env to hold a Census key.
setup:
    cd analysis && uv sync
    [ -f .env ] || cp .env.example .env

# Build every result: minutes with the runs on disk, about five hours without them.
build *args:
    uv run --project analysis python -m manuscript_analysis {{args}}

# Rebuild and compare with what is committed: run before and after every change.
check:
    uv run --project analysis python scripts/check.py

# Open the notebooks in JupyterLab.
notebooks:
    uv run --project analysis jupyter lab analysis/manuscript_analysis

# Mirror the prose from the Overleaf clone into manuscript/ (--apply to copy).
sync-manuscript *args:
    scripts/sync-manuscript.sh {{args}}

# Copy the generated figures and tables into the Overleaf clone (--apply to copy).
publish *args:
    scripts/publish-results.sh {{args}}

# Word copies of the manuscript and supplement for collaborators; needs pandoc.
docx:
    uv run --project analysis scripts/build-docx.sh

# Delete what `build` regenerates. Never the runs, and never a checksum file.
clean:
    rm -rf results/demos/figures results/demos/tables
    rm -f results/demos/demo-*.ipynb
    find results/lit-search -type f ! -name MANIFEST.sha256 -delete
