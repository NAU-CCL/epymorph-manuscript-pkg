# https://just.systems. Run `just` for the list. Every recipe runs from the repository root.

# A Census key in .env reaches epymorph this way. Builds do not need one: every Census
# input is frozen in data/raw/. Only refreshing an input does.
set dotenv-load

# List the recipes.
default:
    @just --list --unsorted

# Set up your development environment.
setup:
    cd analysis && uv sync
    [ -f .env ] || cp .env.example .env

# Re-fetch the CDC observations into the specified `folder`.
fetch-observations folder:
    mkdir -p {{folder}}
    uv run --project analysis python -m manuscript_analysis.fetch_flu_observations {{folder}}/flu-observations.csv
    uv run --project analysis python -m manuscript_analysis.fetch_covid_observations {{folder}}/covid-observations.csv
    -cmp data/demos/flu/observations.csv {{folder}}/flu-observations.csv && echo "flu: identical to the frozen file"
    -cmp data/demos/covid/observations.csv {{folder}}/covid-observations.csv && echo "covid: identical to the frozen file"

# Build every result: minutes with the runs on disk, about five hours without them.
build *args:
    uv run --project analysis python -m manuscript_analysis {{args}}

# Rebuild and compare with what is committed: run before and after every change.
check:
    uv run --project analysis python scripts/check.py

# Open the notebooks in JupyterLab.
notebooks:
    uv run --project analysis jupyter lab analysis/manuscript_analysis

# Word copies of the manuscript and supplement for collaborators; needs pandoc.
docx:
    uv run --project analysis python scripts/build_docx.py

# Delete what `build` regenerates. Never the runs, and never a checksum file.
clean:
    rm -rf results/demos/figures results/demos/tables
    rm -f results/demos/demo-*.ipynb
    find results/lit-search -type f ! -name MANIFEST.sha256 -delete

# Set up Overleaf sync: provide the URL for the Overleaf project's git repo.
setup-overleaf url:
    git clone {{url}} .overleaf

# Sync with Overleaf (two-way).
overleaf-sync:
    # Push local changes to .overleaf
    rsync -av --delete manuscript/ .overleaf/ --exclude .git/

    # Commit any local changes in .overleaf
    if [ -n "$(git -C .overleaf status --porcelain)" ]; then \
        git -C .overleaf add --all && git -C .overleaf commit -m "Sync manuscript changes to Overleaf"; \
    fi

    # Two-way sync with Overleaf: pull changes, rebase local, then push.
    git -C .overleaf pull --rebase origin main
    git -C .overleaf push origin main
    
    # Integrate changes from the Overleaf submodule back into the main repository.
    # Exclude changes to generated files -- these shouldn't be edited in Overleaf.
    rsync -av --delete .overleaf/ manuscript/ --exclude .git/ --exclude generated/

    # Commit any changes now in the manuscript directory.
    git add -- manuscript
    if [ -n "$(git diff --cached --name-only -- manuscript)" ]; then \
        git commit -m "Sync manuscript changes from Overleaf" -- manuscript; \
    fi
    git push origin main
