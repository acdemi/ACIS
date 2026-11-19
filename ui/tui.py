"""Deprecated TUI launcher: use ``python -m acis tui`` instead."""

from __future__ import annotations

import sys
import warnings

from acis.config import load_env

load_env()

from acis.ui import tui as _tui  # noqa: E402

_DEPRECATION = (
    "`python -m ui.tui` is deprecated; use `python -m acis tui` instead."
)


def __getattr__(name: str):
    """Expose the current TUI module's attributes for backwards imports."""
    return getattr(_tui, name)


def main() -> None:
    warnings.warn(_DEPRECATION, DeprecationWarning, stacklevel=2)
    _tui.main()


if __name__ == "__main__":
    print(_DEPRECATION, file=sys.stderr)
    main()
