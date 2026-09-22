"""Flu model definitions for the Demo 1 comparison.

Each module exports one or more `ForecastModel` objects. Everything the models share
lives in `flu_season.py`, so a model module contains only what distinguishes it.

The Census API key is loaded here, since the demography ADRIOs need it however the
models are driven.
"""

from dotenv import load_dotenv

from ... import paths

# The Census API key, for the demography and commuting ADRIOs. Loaded here because the
# models need it however they are driven: the CLI, a notebook, or the exporter.
load_dotenv(paths.ROOT / ".env")
