"""IPM factory functions, one module per structural variant.

Each module exposes a *factory function*, never a module-level model instance,
so that structural options are arguments and a notebook can build several
variants without restarting the kernel.
"""
