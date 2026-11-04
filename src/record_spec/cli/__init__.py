"""The record-spec command-line interface.

A click-based translation of the Kotlin ``record-spec-cmd`` module. Invoke
as ``record-spec`` (console script) or ``python -m record_spec``.
"""

from __future__ import annotations

from record_spec.cli.main import main

__all__ = ["main"]