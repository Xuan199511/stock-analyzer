"""Central loguru configuration for deep-analysis modules.

Import `logger` from here in any deep_analysis module.  First import
bootstraps the sink; subsequent imports are no-ops.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from loguru import logger

_CONFIGURED = False
_LOG_DIR = Path(os.getenv("ANALYSIS_LOG_DIR", "logs"))
_LEVEL = os.getenv("ANALYSIS_LOG_LEVEL", "INFO").upper()


def _configure() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    logger.remove()
    fmt = (
        "<green>{time:HH:mm:ss}</green> "
        "<level>{level: <7}</level> "
        "<cyan>{extra[section]}</cyan> "
        "<level>{message}</level>"
    )
    logger.configure(extra={"section": "-"})
    logger.add(sys.stderr, level=_LEVEL, format=fmt, colorize=True, enqueue=False)
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        logger.add(
            _LOG_DIR / "analysis.log",
            level=_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} {level: <7} [{extra[section]}] {message}",
            rotation="5 MB",
            retention=5,
            encoding="utf-8",
            enqueue=True,
        )
    except Exception as e:
        logger.warning(f"file log disabled: {e}")
    _CONFIGURED = True


_configure()

__all__ = ["logger"]
