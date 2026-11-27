"""Configure logging once for the whole project.

Only entry points (scripts, the dashboard, CLI commands) call ``setup_logging()``.
Every other module just does:

    import logging
    logger = logging.getLogger(__name__)
    logger.info("Something happened")
"""

import logging
import os
import sys
from pathlib import Path

LOG_LEVEL_ENV_VAR = "CLAIM_SEVERITY_LOG_LEVEL"  # e.g. set to DEBUG for more detail
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str | None = None, log_file: str | Path | None = None) -> None:
    """Send log messages to the terminal and, optionally, to a file.

    Which level is used, in order of priority:
    1. ``level``, if given
    2. the ``CLAIM_SEVERITY_LOG_LEVEL`` environment variable, if set
    3. ``INFO``
    """
    chosen = (level or os.environ.get(LOG_LEVEL_ENV_VAR) or DEFAULT_LOG_LEVEL).upper()
    if chosen not in logging.getLevelNamesMapping():
        raise ValueError(f"Unknown log level {chosen!r}. Use DEBUG, INFO, WARNING or ERROR.")

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file is not None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))

    # force=True replaces any earlier setup, so calling this twice never duplicates messages.
    logging.basicConfig(
        level=chosen,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=handlers,
        force=True,
    )
