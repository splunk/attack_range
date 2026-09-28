import logging

from attack_range.logger import setup_logging


def test_setup_logging_is_idempotent(tmp_path):
    log_path = tmp_path / "attack_range.log"
    logger = logging.getLogger("attack_range")
    logger.handlers.clear()

    first = setup_logging(str(log_path), "INFO")
    second = setup_logging(str(log_path), "INFO")

    assert first is second
    assert len(logger.handlers) == 2

    emitted = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            emitted.append(record.getMessage())

    capture = CaptureHandler()
    logger.addHandler(capture)
    try:
        logger.info("once")
        assert emitted.count("once") == 1
    finally:
        logger.removeHandler(capture)
        logger.handlers.clear()
