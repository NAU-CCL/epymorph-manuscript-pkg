# Adding a figure

Three places a figure can live, and which one is right depends on **who needs it**, not on
how much work it is.

| you want to... | put it | tracked by git |
|---|---|---|
| look at something, or drop it in a talk | a notebook cell, `figure_dir=NOTEBOOK_FIGURES` | no |
| draw a new *kind* of panel | a `figure_*` in `flu/evaluation.py` or `covid/evaluation.py` | n/a, it is code |
| put it in the paper | a composer in `export.py` | **yes** |

The rule behind the table: **a figure in the paper must be something `build-figures.sh`
produces.** If it exists only because someone ran a notebook cell by hand, nothing
regenerates it, `check.sh` cannot see it, and in six months nobody can tell whether it
still matches the runs. That is the failure this repository is built to prevent, so
changing `figure_dir` in a notebook is the wrong way to get a figure into the supplement
even though it works mechanically.

---

## The division of labour

**`flu/evaluation.py` and `covid/evaluation.py` own the drawing.** Every `figure_*` there
draws one panel or one row of panels from the run outputs, and knows about epymorph, the
scores and the models.

**`export.py` owns the layout, and nothing else.** It decides which panels sit in which
grid with which letters. It contains no drawing code and no knowledge of the data. That
split is what lets a panel be tuned once and have both the notebook and the paper follow.

### Naming

Because the two layers do different jobs, they are named differently, and a name should
say which layer it belongs to:

| layer | pattern | examples |
|---|---|---|
| panels, in `*/evaluation.py` | `figure_<what it draws>` | `figure_fit_by_age`, `figure_rolling_forecasts` |
| composers, in `export.py` | `figure_<n>_<demo>` or `figure_s_<what>` | `figure_2_flu`, `figure_s_calibration` |

A main-text composer is named for its **number**; a supplementary one takes `figure_s_`,
matching the `figS-` file prefix and the `figure-s-` keys in `FIGURES`. A composer is never
named after the panel function it calls: `figure_s_flu_fit` and `flu.figure_fit_by_age` are
different things, and the names should not have to be read carefully to tell them apart.

---

## Adding a manuscript figure

Three edits in `export.py`, all near each other.

### 1. Write the composer

```python
def figure_s_flu_fit(ev, model=FLU_MODEL):
    """Supplementary: the filter's weekly fit at the six age bands.

    (a) the prior, a genuine one-week-ahead prediction; (b) the posterior, which is
    pulled onto the observation by construction. The gap between them is how hard the
    filter had to work.
    """
    fig = plt.figure(figsize=(DOUBLE_COLUMN, 7.4), layout="constrained")
    prior, posterior = fig.subfigures(2, 1)
    flu.figure_fit_by_age(ev, flu.FOCUS_STATE, model, series="prior",
                          title=None, subfig=prior)
    flu.figure_fit_by_age(ev, flu.FOCUS_STATE, model, series="posterior",
                          title=None, subfig=posterior)
    label_panels([prior, posterior])
    return fig
```

### 2. Register it

```python
FIGURES = (
    "figure-2",
    ...
    "figure-s-flu-fit",          # <- add
)
```

### 3. Build it in `main()`

Put it beside the demo whose evaluation it needs, so `flu_ev` is already loaded:

```python
    if "figure-s-flu-fit" in wanted:
        fig = figure_s_flu_fit(flu_ev)
        written += save_figure(fig, "figS-flu-fit-by-age", args.figures_dir)
        plt.close(fig)
```

That is all. `publish-results.sh` needs no change: it globs
`results/demos/figures/*.pdf`, so the new figure reaches Overleaf on the next run.

---

## The contract every panel function satisfies

You can rely on all of these, and a new panel function should provide them:

- **`subfig=`** — draw into a `SubFigure` instead of making a standalone figure. This is
  what makes composition possible.
- **`title=`** — `"auto"` for the built-in title, `None` for none, or a string. A panel
  inside a composed figure always passes `None`: the caption carries what the title would
  have said. See `lib/figures.resolve_title`.
- **`color=`** — on the fit and forecast panels, to override the model's colour. Used by
  the supplementary forecast figures to draw the model's own resolution in
  `lib.figures.FINE_SCALE`, a darker shade, so two resolutions of one model do not read as
  two models.

---

## Layout notes worth knowing

**Subfigures, not gridspec.** Each panel is a `SubFigure` so the panel function can lay out
its own axes inside it. Split with `fig.subfigures(rows, cols, height_ratios=[...])` and
nest freely: `figure_3_covid` puts `(a)` and `(b)` side by side in its top row because the
commuting matrix is square and would otherwise waste half a row.

**`label_panels`** takes the subfigures in reading order and stamps `(a)`, `(b)`, ... at the
top left of each. Pass them left-to-right then top-to-bottom, which is not always the order
you created them in.

**Legends inside side-by-side subfigures.** Matplotlib places an `"outside"` legend against
the *parent* figure, so two side-by-side panels both putting a legend outside will stack
them on top of each other. Pass `legend="axes"` to put it inside the panel instead;
`figure_s_calibration` does exactly this for that reason.

**Never leave a legend on `loc="best"`.** It asks the renderer which position overlaps the
data least, and the answer is not stable between runs: it made the calibration figure's PNG
flip between two byte values on alternate builds. Pass an explicit corner. Figure output
should be reproducible for the same reason the ensembles are.

**Page limits.** `DOUBLE_COLUMN` is 7.2 in wide, and a figure should stay under about
9.4 in tall to leave room for a caption. Both main-text figures are 8.3 in.

---

## Then check it

```bash
scripts/build-figures.sh     # writes results/demos/figures/
scripts/check.sh             # tables and the run manifest still agree
```

If the figure is meant to *replace* something, delete the old file from
`results/demos/figures/` as well: nothing prunes it, and a stale PDF would keep being
published to Overleaf.

---

## Candidates not yet promoted

Panels the notebooks draw that are not yet part of any composed figure, if you are looking
for what the supplement might still want:

| panel | what it shows |
|---|---|
| `flu.figure_fit_by_age`, prior and posterior | the six fitted channels, before and after the update |
| `flu.figure_eta_by_age` | the per-age contact correction through the season |
| `covid.figure_fit(ev, "state")` | the state model's fit, displaced when Figure 3(b) became the county fit |
| `covid.figure_rolling_forecasts(ev, "county", ...)` | the movement-off contrast at the same counties |
