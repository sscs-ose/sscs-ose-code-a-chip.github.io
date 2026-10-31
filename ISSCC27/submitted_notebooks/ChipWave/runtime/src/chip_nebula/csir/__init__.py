"""Chip Nebula bundled Compact SpecIR v0.1 compiler."""

__version__ = "0.1.0"
__upstream_commit__ = "5cea790d4aba04ca810d710290bcb5fd7e47745d"

from .parser import parse
from .semantics import check

__all__ = ["check", "parse", "__upstream_commit__", "__version__"]
