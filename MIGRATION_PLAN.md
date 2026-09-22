# epymorph-manuscript-pkg — Migration & Reproducibility Plan

_Working plan for building this repo as a reproducible companion to the epymorph manuscript. Originally developed with Claude (Cowork), 2026-09-14/15. Kept here for posterity / to hand off to other tools (e.g. Claude Code)._

## Working preference (applies to every step below)

- **Joe runs all git commands himself (2026-09-14).** For every repo in this project
  (this monorepo, `epymorph_ms_overleaf/`, any future ones) — `git add`, `git commit`,
  and `git push` are all run by Joe in his own local terminal, even in repos/cases
  where an assistant could technically run them directly (e.g. local-only commits with
  no remote or credentials involved). Assistant's role: edit/prepare files, then tell
  Joe exactly which git commands to run and when (with the working directory and a
  suggested commit message).

## Progress

- **Step 1 DONE (2026-09-14).** Repo created at
  `/Users/jrm846/Documents/Claude/Projects/epymorph-manuscript-pkg/`, git initialized
  (local only, no remote). Contains: `README.md`, `LICENSE` (GPL-3.0 full text),
  `LICENSE-MANUSCRIPT.md` (CC-BY-4.0 notice), `CITATION.cff`, `.gitignore`, and
  `data/`, `analysis/`, `manuscript/`, `results/`, `scripts/` each with a README
  explaining its purpose and which later step populates it. Deeper subdirectories
  (`src/`, `notebooks/`, `sections/`, etc.) were deliberately NOT pre-created — they
  get created exactly when populated, in later steps below.
  - Note: if a `.git/index.lock` gets stuck, delete it manually via Finder/Terminal.
- **REORDERED (2026-09-14): Step 2 (migrate analysis code / demolib) is DEFERRED.**
  Joe doesn't want to migrate the demolib scripts yet — they're not finalized. New
  order: **Overleaf setup (in progress, see below), then lit-search condensing (old
  Step 4), then back to analysis code / notebooks (old Steps 2-3) once those are more
  settled.** The step numbers below are kept as originally written for reference; just
  don't assume they run in numeric order — follow "Next up" here instead.
- **Overleaf setup — IN PROGRESS (2026-09-14).**
  - Overleaf project created from the Springer Nature LaTeX Template (renamed by Joe
    in Overleaf's UI). Template contents: `sn-jnl.cls` (Springer Nature class),
    `sn-article.tex` (sample main file, left in place untouched as reference),
    `sn-bibliography.bib` (sample refs), bibliography styles for several citation
    formats (`sn-mathphys-ay.bst`, `sn-vancouver-ay.bst`, `sn-nature.bst`,
    `sn-chicago.bst`, `sn-apacite.bst`, `sn-basic.bst`, `sn-aps.bst`,
    `sn-mathphys-num.bst` — relevant once Nature Methods vs. Communications is
    decided), sample figures (`empty.eps`, `fig.eps`), a compiled sample
    `sn-article.pdf`, and `user-manual.pdf`.
  - **Using Overleaf's GitHub integration, not the plain Git integration** (Joe
    already had GitHub integration connected). GitHub sync is manual/button-driven
    only inside Overleaf's UI ("Push Overleaf changes to GitHub" button, and a pull
    option) — synchronization between GitHub and Overleaf does not happen
    automatically. Since the Overleaf project already existed (from the template),
    Joe used the "create a new GitHub repository from this existing project"
    direction. Result: a private GitHub repo,
    `https://github.com/joseph-mihaljevic/epymorph_ms_overleaf`. This is a conscious
    split from the monorepo's still-local-only status — Joe is fine with the
    manuscript being on GitHub now and the monorepo following later.
  - Cloned locally (by Joe, in his own terminal) to
    `/Users/jrm846/Documents/Claude/Projects/epymorph_ms_overleaf/` (kept this name —
    distinguishes it from other manuscript projects he might work on later).
    `git remote -v` confirmed pointing at the GitHub repo, on branch `main`.
  - **First real round-trip completed (2026-09-14):** built a placeholder-only modular
    LaTeX scaffold (see Step 5 below) in the monorepo's `manuscript/`, copied it into
    `epymorph_ms_overleaf/`, Joe ran `git add`/`commit`/`push` himself in both repos,
    pulled into Overleaf's live editor, set `main.tex` as the main document, and
    recompiled successfully. This confirms the whole loop works end to end.
  - **Still to do for Overleaf setup:** design the actual ongoing sync workflow between
    `epymorph_ms_overleaf/` and `epymorph-manuscript-pkg/manuscript/` for when real
    content starts flowing (assistant prepares/copies files, Joe runs the git commands
    on both ends); pin down Nature Methods vs. Nature Communications before final
    formatting (still open, not blocking).
- **Next up: continue Overleaf setup** (formalize the sync workflow) **or** start
  lit-search condensing.

## Decision record (settled 2026-09-14)

- **New repo name/location:** `epymorph-manuscript-pkg`, sibling to the original working
  folder → `/Users/jrm846/Documents/Claude/Projects/epymorph-manuscript-pkg/`.
- **Original folder** (`/Users/jrm846/Documents/Claude/Projects/epymorph-manuscript/`)
  stays exactly as-is — it is NOT migrated. It remains Joe's private working folder
  (knowledge-base/, project-notes/, scratch/, writing-examples/, bug-reports/,
  seasonality-plan.md). Only genuinely reproducible artifacts move to the new repo.
- **git/GitHub (monorepo):** local `git init` only for now. No GitHub remote yet for
  `epymorph-manuscript-pkg` — add later once structure has settled. (The MANUSCRIPT's
  Overleaf-linked repo is a separate, deliberate exception — see Overleaf progress
  above.)
- **License:** GPL-3.0 for the analysis code (matches epymorph itself — NAU-CCL/Epymorph
  on Zenodo is GPL-3.0-only, and the analysis code directly depends on/exercises it, so
  matching avoids copyleft-compatibility ambiguity). CC-BY-4.0 for the manuscript text.
  Both recorded in `LICENSE` + `LICENSE-MANUSCRIPT.md` + `CITATION.cff`.
- **Structure is meant to be a generic template**, not epymorph-specific — Joe wants
  something any future python-project + manuscript could reuse. Concretely: no
  "epymorph" branding baked into the analysis package name, and no directory that only
  makes sense for this one project.
- **FINAL AGREED DIRECTORY TREE** (confirmed 2026-09-14; Step 1 built the top-level
  parts of this, marked ✅ below — the rest arrives in later steps):
  ```
  epymorph-manuscript-pkg/
  ├── README.md                        ✅
  ├── LICENSE                          ✅ GPL-3.0 (code)
  ├── LICENSE-MANUSCRIPT.md            ✅ CC-BY-4.0 (manuscript text/figures)
  ├── CITATION.cff                     ✅
  ├── .gitignore                       ✅
  │
  ├── data/                            ✅ (README only so far)
  │   ├── raw/
  │   │   └── lit-search/              ← PubMed/Lens exports (lit-search condensing step)
  │   └── processed/
  │
  ├── analysis/                        ✅ (README only so far) — DEFERRED, demolib not finalized
  │   ├── pyproject.toml
  │   ├── uv.lock
  │   ├── .python-version
  │   ├── src/
  │   │   └── manuscript_analysis/     ← generic package name (was epymorph_ms — rejected,
  │   │       │                          too tied to epymorph branding)
  │   │       ├── __init__.py
  │   │       ├── ipms/, params/, plots/   ← from demolib/ (old folder)
  │   │       ├── contacts.py, cache.py, figures.py, likelihoods.py, scoring.py
  │   │       └── lit_search/          ← simplified screening pipeline (lit-search step)
  │   └── notebooks/                   ← driver notebooks that call src/; nested INSIDE
  │       ├── demo-flu/                  analysis/, not a top-level sibling (Joe's call —
  │       └── demo-covid/                keeps the top-level tree generic; a script-only
  │                                       future project just wouldn't populate this)
  │
  ├── manuscript/                      ✅ DONE — modular LaTeX scaffold built (Springer
  │   ├── main.tex                       Nature template, sn-nature class option),
  │   ├── sections/                      placeholder content only, no real prose ported
  │   │   ├── 01-introduction.tex        yet. Committed in both the monorepo and
  │   │   ├── 02-methods.tex             epymorph_ms_overleaf/, pushed/pulled/recompiled
  │   │   ├── 03-results.tex             successfully in Overleaf.
  │   │   └── 04-discussion.tex
  │   ├── supplementary/
  │   │   ├── supplement-main.tex
  │   │   ├── S1-software-landscape.tex
  │   │   └── S2-parameter-estimation.tex
  │   ├── references.bib               ← empty, awaiting Zotero Better BibTeX export
  │   ├── sn-jnl.cls, sn-*.bst          ← copied from the Overleaf template so this
  │   │                                   compiles standalone, not just inside Overleaf
  │   └── README.md                    ← explains the modularity-vs-template tension
  │                                       (see decision record entry below) and the
  │                                       sync relationship with epymorph_ms_overleaf/
  │
  ├── results/                         ✅ (README only so far)
  │   ├── figures/
  │   ├── manuscript/                  ← compiled PDF
  │   ├── lit-search/                  ← shortlists, register, PRISMA diagram (lit-search step)
  │   ├── manuscript-numbers.tex       ← auto-generated macros (see mechanism below)
  │   └── checksums.sha256
  │
  └── scripts/                         ✅ (README only so far)
      ├── build.sh
      └── check.sh
  ```
- **Modularity vs. the Springer Nature template:** `sn-article.tex` itself says "Please
  do not use \input{...} to include other tex files. Submit your LaTeX manuscript as
  one .tex document," and Nature Portfolio's eJP submission system wants references
  pasted directly into the file rather than a `\bibliography{}` call. Verified this is
  a SUBMISSION-FORMAT requirement, not a technical limitation — `\input` compiles fine
  under `sn-jnl.cls` and on Overleaf (confirmed by the successful scaffold compile).
  Resolution: draft modularly as planned (one file per section, easier to diff/review
  in git); add a "flatten" step to `scripts/build.sh` (Step 7, not yet written) that
  concatenates everything into one file at submission time.
- **Overleaf/git topology:** manuscript is a SEPARATE repo (GitHub, via Overleaf's
  GitHub sync — see Overleaf progress above for why this changed from the originally
  planned plain-git-integration approach), not a submodule/subtree of the monorepo.
  Monorepo is the reproducibility source of truth. Sync workflow (respecting the "Joe
  runs all git commands" preference above): prepare/copy files into both
  `epymorph-manuscript-pkg/manuscript/` and `epymorph_ms_overleaf/`, then Joe runs
  `git add`/`commit`/`push` in each as prompted; on the Overleaf side, Joe also clicks
  **Pull** in Overleaf's GitHub panel to bring changes into the live editor, and
  **Push Overleaf changes to GitHub** to send his in-editor edits back out (which Joe
  then `git pull`s locally before the resolved prose gets copied into the monorepo).
  Not continuous — collaborators use Overleaf's native comments/track-changes, which
  never travel through git at all; sync happens at review milestones.
- **Target journal (Nature Methods vs. Nature Communications): still undecided, and
  that's fine.** Nothing so far depends on it, and the Springer Nature template covers
  both (separate .bst files per citation style are already in the template). Pin it
  down only before the final formatting pass (author guidelines, length limits, and
  reference style differ between the two).
- **Reproducible numbers in LaTeX:** no live code execution in .tex (ruled out PythonTeX/
  SageTeX — Overleaf's shared compile servers don't support the shell-escape/arbitrary
  execution they need). Instead: analysis writes final numbers to an auto-generated
  `results/manuscript-numbers.tex` of `\newcommand` macros (or a CSV read via `datatool`/
  `csvsimple` for whole tables); `main.tex` does `\input` once; prose uses the macros
  instead of typed literals. Rerun analysis → regenerate macros → sync to
  `epymorph_ms_overleaf/` → Joe pushes + pulls in Overleaf → recompile → every
  reference updates. Anchor point: `drafts/intro-v05.md` line 13's
  `[DEMONSTRATION: ...]` / `[HEADLINE RESULT: ...]` placeholders are exactly where these
  macros will go once the demo vignettes produce final numbers.

## Open items, resolved just-in-time

- Whether `knowledge-base/filtering-software-review-Jul2026.md` (in the original
  folder) is superseded by the unified `software-lit-search/` pipeline or needs
  separate treatment — check during the lit-search condensing step.
- Final Nature Methods vs. Nature Communications choice — before the final formatting pass.
- Exact shape of the ongoing sync workflow between `epymorph_ms_overleaf/` and
  `epymorph-manuscript-pkg/manuscript/` once real content (not just the scaffold) is
  flowing both ways.

## The steps (original numbering kept for reference — see "Progress" above for actual order)

1. ✅ **DONE — Scaffold the repo.**
2. **DEFERRED — Migrate analysis code.** `demolib/` (original folder) → `analysis/src/manuscript_analysis/`
   (rename package, fix internal imports); relocate `pyproject.toml`/`uv.lock`/
   `.python-version`; confirm `uv sync` + a smoke import still work. Deferred because the
   demolib scripts aren't finalized yet.
3. **DEFERRED — Migrate demo notebooks.** Final (non-superseded) `demo-flu/*.ipynb` and
   `demo-covid/*.ipynb` → `analysis/notebooks/demo-flu/`, `analysis/notebooks/demo-covid/`.
   Decide fate of each `superseded/` subfolder and the loose methods-notes .md files
   living next to the notebooks (contact-matrix-methods*.md, ihr-revision.md,
   data-coverage.html, etc.).
4. **NEXT-NEXT — Revisit, simplify, then migrate the lit-search pipeline.** Full revisit
   of `software-lit-search/` to reduce the number of files (currently 5 scripts, 3 raw
   exports, ~7 `unified_*` output files, plus a `superseded/` archive) — NOT a straight
   lift-and-shift. Two passes: (a) redesign/simplify the pipeline first — where it lives
   now or in a scratch copy — confirming it still reproduces the same headline counts
   (currently: PubMed 2,364→437, Lens 1,009→208, total 3,033→645); (b) migrate the
   simplified version into `data/raw/lit-search/` (raw exports),
   `analysis/src/manuscript_analysis/lit_search/` (scripts), `results/lit-search/`
   (shortlists, `software-candidate-register.xlsx`, PRISMA diagram — currently in
   `drafts/`). One README tying provenance together, replacing the three
   currently-separate homes (`software-lit-search/`, `lit/`,
   `knowledge-base/related-software.md`). Do NOT commit the competitor-package PDFs
   tracked by `lit/` (copyright) — keep only the link/metadata registry. Resolve the
   filtering-software-review-Jul2026.md question during pass (a). Given the file count,
   treat this as its own dedicated chat (maybe two: one for the redesign, one for the
   migration).
5. ✅ **DONE — Modular LaTeX scaffold.** Built with placeholder content only — see
   Progress and the directory tree above. Real content (from `drafts/intro-v05.md`,
   `drafts/methods_v05.md`, and the appendix drafts) still needs to be ported in; that
   remains a future step once Joe is ready to move real prose over.
6. **IN PROGRESS — Overleaf setup + tutorial.** Project created from the Springer Nature
   template; GitHub sync connected (`epymorph_ms_overleaf` repo, private); cloned to
   `epymorph_ms_overleaf/` locally; scaffold round-trip completed successfully (see
   Progress). Remaining: formalize the ongoing sync workflow for real content, pin down
   Nature Methods vs. Nature Communications before the final formatting pass.
7. **Wire up build/check.** `scripts/build.sh` (analysis → figures → numbers →
   compile manuscript, PLUS the "flatten to one file" step for submission — see the
   modularity-vs-template decision above), `scripts/check.sh`, `results/checksums.sha256`.
8. **Containerization (deferred).** Docker or Apptainer, once content has settled —
   note Monsoon (Joe's HPC) needs Apptainer, so Docker would need conversion later if
   chosen first.
