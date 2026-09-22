"""
Canonical pre-filter lexicon for the epymorph software-landscape screen.

ONE lexicon is applied to every source (PubMed, Lens.org). This module is the single
point of truth: the term sets printed in Appendix S1 §S1.1 are generated from here by
`print_lexicon.py`, so the manuscript and the executed screen cannot drift apart.

History: the first pass (July 2026) inadvertently ran three different lexicons across
its three legs (scripts/screen.py, lens_screen.py, lensb_screen.py). These sets are the
union of those three, i.e. the most recall-oriented of the variants actually used. The
v1 scripts and their outputs are retained in this directory for provenance.
"""

# --- A: software / artifact signal -------------------------------------------------
SOFT = [
    r'\bpackage\b', r'\bsoftware\b', r'\btoolkit\b', r'\btoolbox\b', r'\blibrary\b',
    r'\bframework\b', r'open[- ]source', r'freely available', r'available at',
    r'available from', r'github', r'\bcran\b', r'\bpypi\b', r'implemented in',
    r'\br package\b', r'python package', r'\bjulia\b', r'\bwe (present|introduce|develop)',
]

# --- B: inference / uncertainty-quantification signal -------------------------------
METH = [
    r'particle filter', r'sequential monte carlo', r'\bsmc\b', r'ensemble kalman',
    r'kalman filter', r'data assimilation', r'\bbayesian\b',
    r'markov chain monte carlo', r'\bmcmc\b', r'approximate bayesian',
    r'\babc[- ]smc\b', r'\bpmcmc\b', r'state[- ]space', r'nested sampling',
    r'hamiltonian monte carlo', r'uncertainty quantif', r'quantified uncertainty',
    r'\bemulat', r'history matching', r'iterated filtering', r'parameter estimation',
    r'\bcalibrat', r'likelihood',
]

# --- C: epidemiological domain signal ------------------------------------------------
DOM = [
    r'epidemic', r'compartmental', r'\bseir\b', r'\bsir model', r'metapopulation',
    r'meta-population', r'transmission', r'infectious disease', r'outbreak',
    r'\bforecast', r'influenza', r'covid', r'dengue', r'malaria', r'measles',
    r'mpox', r'ebola', r'pandemic',
]

# --- sequential-filtering subset (reported separately, not an inclusion gate) --------
FILT = [
    r'particle filter', r'ensemble kalman', r'kalman filter', r'sequential monte carlo',
    r'data assimilation', r'\bsmc2?\b', r'\bpmcmc\b',
]

# --- packages already in the candidate register --------------------------------------
# Used only to label records, never to decide them. Terms that collide with ordinary
# English (surveillance, dust, odin) are matched in a word-boundary-and-context form so
# the label means what it says; see `known_hits()`.
KNOWN = [
    # (display name, pattern). The name is what lands in the `known` column and in the R1
    # reason, so it must read as a package name: the column used to carry raw patterns, which
    # was harmless for matching but leaked regex into hand-written prose.
    # Two spellings of the surveillance package share one name; `known_names` dedupes.
    ("epymorph", r'\bepymorph\b'),
    ("FlepiMoP", r'\bflepimop\b'),
    ("spatPomp", r'\bspatpomp\b'),
    ("pomp", r'\bpomp\b(?! )'),
    ("odin", r'\bodin2?\b'),
    ("dust", r'\bdust2?\b(?!\s*(particle|storm|mite|exposure))'),
    ("mcstate", r'\bmcstate\b'),
    ("monty", r'\bmonty\b'),
    ("LibBi", r'\blibbi\b'),
    ("rbi", r'\brbi\b'),
    ("SimInf", r'\bsiminf\b'),
    ("PyRoss", r'\bpyross\b'),
    ("hhh4", r'\bhhh4\b'),
    ("EpiModel", r'\bepimodel\b'),
    ("Epydemix", r'\bepydemix\b'),
    ("pypfilt", r'\bpypfilt\b'),
    ("epifx", r'\bepifx\b'),
    ("bssm", r'\bbssm\b'),
    ("SimBIID", r'\bsimbiid\b'),
    ("epidemia", r'\bepidemia\b'),
    ("Pathogen.jl", r'pathogen\.jl'),
    ("BayesianFitForecast", r'\bbayesianfitforecast\b'),
    ("Bernadette", r'\bbernadette\b'),
    ("epinet", r'\bepinet\b'),
    ("MEmilio", r'\bmemilio\b'),
    ("SPARSEMODr", r'\bsparsemodr\b'),
    ("Starsim", r'\bstarsim\b'),
    ("EpiEstim", r'\bepiestim\b'),
    ("EpiNow2", r'\bepinow2\b'),
    ("tsiR", r'\btsir\b'),
    ("nosoi", r'\bnosoi\b'),
    ("epiworldR", r'\bepiworldr\b'),
    ("outbreaker2", r'\boutbreaker2?\b'),
    ("MetaRVM", r'\bmetarvm\b'),
    ("gemlib", r'\bgemlib\b'),
    ("tsgc", r'\btsgc\b'),
    ("hmer", r'\bhmer\b'),
    ("eSIR", r'\besir\b'),
    ("NGSSEML", r'\bngsseml\b'),
    ("EpiILM", r'\bepiilm(ct)?\b'),
    ("ParticleDA.jl", r'\bparticleda\b'),
    ("QuantDiffForecast", r'\bquantdiffforecast\b'),
    ("EpiLPS", r'\bepilps\b'),
    ("aghq", r'\baghq\b'),
    ("surveillance", r'\bsurveillance package\b'),
    ("surveillance", r'\bR package surveillance\b'),
]

# Named, not lettered. Appendix S1.1's *retrieval* query also labels three blocks A/B/C,
# but there A is the domain and C is the artifact, the opposite of the assignment these
# screening blocks once used. Words remove the collision.
BLOCKS = {'software': SOFT, 'inference': METH, 'epidemiology': DOM}
