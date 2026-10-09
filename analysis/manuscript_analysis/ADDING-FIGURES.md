# Adding a figure

**`plots.py` draws a panel; the notebook lays out the figure.** Every figure in the paper
is assembled in section 9 of its demo's notebook (`demo-flu.ipynb` or `demo-covid.ipynb`)
from panels that `plots.py` draws, and saved by the build.

Where something belongs depends on **who needs it**, not on how much work it is:

| you want to... | put it | in git |
|---|---|---|
| look at something | a notebook cell that ends in `plt.show()` | no; the executed notebook in `results/demos/` keeps it |
| draw a new *kind* of panel | a function in `plots.py` | it is code |
| put it in the paper | a cell in section 9 of the notebook that ends in `save(fig, name)` | **yes**, `results/demos/figures/` |

The rule behind the table: **a figure in the paper must be something `just build`
produces.** If it exists only because someone saved it by hand, nothing regenerates it,
`just check` cannot see it, and in six months nobody can tell whether it still matches the
runs. That is the failure this repository is built to prevent.

---

## The division of labour

**`plots.py` owns the drawing.** Its functions take plain numpy arrays and pandas tables
and know nothing about epymorph, the scores or either demo, so both demos draw the same
kind of panel with the same function. There are two kinds:

| kind | takes | examples |
|---|---|---|
| axes-level | an `ax` to draw into | `plot_contact_matrix`, `plot_flow_matrix`, `plot_ratio_swarm`, `plot_rolling_forecasts` |
| grid | `subfig=`, and lays out its own axes inside it | `plot_quantile_grid`, `plot_rolling_forecast_grid`, `plot_single_forecast_grid`, `plot_line_panels` |

**The notebook owns everything else**: which data goes in each panel, which panels make a
figure, their sizes and letters. Each panel is a small `draw_<what>(subfig, ...)` function
in the notebook that selects the data and calls `plots.py`, and the figure itself is a few
lines of layout. Figure 2, from `demo-flu.ipynb`:

```python
fig = plt.figure(figsize=(plots.DOUBLE_COLUMN, 8.3), layout="constrained")
top, channels, benefit = fig.subfigures(3, 1, height_ratios=[2.5, 3.4, 2.4])
structure, skill = top.subfigures(1, 2, width_ratios=[1.9, 1.0])
draw_contacts(structure, FOCUS_STATE)
draw_skill_by_horizon(skill)
draw_fit_by_age(channels, FOCUS_STATE, "multi-strata-empirical")
draw_benefit(benefit)
plots.label_panels([structure, skill, channels, benefit])
save(fig, "fig2-flu-demographic-structure")
```

That split is what lets a reader see exactly what each panel shows, in the notebook,
without reading any drawing code.

---

## Adding a manuscript figure

1. **In section 9 of the demo's notebook**, add a markdown cell saying what the figure
   shows, then a code cell: one `draw_<what>(subfig, ...)` per panel, the layout, and
   `save(fig, name)` last.
2. **Name it** as the others are: `fig<n>-<demo>-<what>` for the main text
   (`fig3-covid-spatial-structure`), `figS-<what>` for the supplement
   (`figS-calibration-flu`).
3. **Build it.** `save` writes a PDF and a PNG to `output_dir/figures/` only when the
   notebook has an `output_dir`, which `just build` gives it; run interactively, the
   notebook shows the figure and writes nothing, so it cannot dirty the committed files.
   Build rather than saving by hand: the build pins `PYTHONHASHSEED`, without which a
   PDF's font subset is ordered differently and its bytes change.

   ```bash
   just build      # writes results/demos/figures/<name>.{pdf,png} and updates checksums.sha256
   just check      # the new figure is compared with a fresh rebuild, pixel for pixel
   ```

4. **Commit** the PDF, the PNG and `results/checksums.sha256` together.
5. **Use it in the manuscript.** `just publish --apply` copies every PDF in
   `results/demos/figures/` into the Overleaf clone; then, in Overleaf,
   `\includegraphics{figures/<name>.pdf}`.

If the figure **replaces** another, delete the old PDF and PNG from
`results/demos/figures/` too: nothing prunes them, so a stale file would stay in
`checksums.sha256` and keep being published. Remove it from the Overleaf project by hand.

---

## Adding a new kind of panel

Add a function to `plots.py` when no existing one draws what you need, and keep it
ignorant of the demos: it takes arrays, dates, labels and colours as arguments, and never
looks up a model, a state or a file. A grid function takes `subfig=None` and gets its axes
from `panel_grid`, so it works standalone and inside a composed figure; if it draws its
own title, it takes `title` and resolves it with `resolve_title` (`"auto"`, `None` or a
string). An axes-level function takes the `ax` first.

---

## Layout notes worth knowing

**Subfigures, not gridspec.** Each panel is a `SubFigure`, so the function drawing it can
lay out its own axes inside it. Split with `fig.subfigures(rows, cols, height_ratios=...)`
and nest freely: Figure 3 puts (a) and (b) side by side in its top row because the
commuting matrix is square and would otherwise waste half a row.

**`label_panels`** takes the subfigures in reading order and stamps (a), (b), ... at the top
left of each. Pass them left to right, then top to bottom, which is not always the order you
created them in; `labels=` continues another figure's lettering (the calibration figures
are (a) for flu and (b) for COVID).

**Legends inside side-by-side subfigures.** Matplotlib places an `"outside"` legend against
the *parent* figure, so two side-by-side panels both putting a legend outside will stack
them on top of each other. `plot_line_panels(legend="axes")` puts it inside the panel
instead, which is how the calibration figures do it.

**Never leave a legend on `loc="best"`.** It asks the renderer which position overlaps the
data least, and the answer is not stable between runs: it once made a figure's PNG flip
between two versions on alternate builds. Pass an explicit corner.

**Page limits.** `plots.DOUBLE_COLUMN` is 7.2 in wide, and a figure should stay under about
9.4 in tall to leave room for a caption. Both main-text figures are 8.3 in.

**Candidates.** Every figure a notebook shows without saving (the data in section 2, the
walkthrough's fit and forecast in section 5, the three-model comparison in section 6) is a
candidate for the supplement; promoting one is the steps above.
