"""
Logging setup for Attack Range.

Creates a shared logging object used by the controller and managers.
"""

import logging


def _resolve_log_level(log_level: str | int) -> int:
    if isinstance(log_level, int):
        return log_level
    return getattr(logging, str(log_level).upper(), logging.INFO)


def setup_logging(log_path: str, log_level: str):
    """
    Creates a shared logging object for the application.

    Idempotent: repeated calls return the same logger without adding duplicate
    handlers. The API creates a new AttackRangeController per request/phase, so
    handler accumulation would otherwise print every log line multiple times.

    :param log_path: Log file path
    :param log_level: Log level (e.g. 'INFO', 'DEBUG')
    :return: Configured Logger instance
    """
    logger = logging.getLogger("attack_range")
    level = _resolve_log_level(log_level)
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        for handler in logger.handlers:
            handler.setLevel(level)
        return logger

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")

    fh = logging.FileHandler(log_path)
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger
