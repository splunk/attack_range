import logging

from attack_range.build_status import can_retry_lab_phase, is_stale_lab_build
from attack_range.managers.config_manager import ConfigManager


def _logger():
    logger = logging.getLogger("test_config_manager_status")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    return logger


def test_can_retry_lab_phase_from_wait_for_vpn():
    assert can_retry_lab_phase("wait_for_vpn")
    assert can_retry_lab_phase("wait_for_vpn", None)


def test_can_retry_lab_phase_from_lab_error():
    assert can_retry_lab_phase("error", "build_lab")
    assert can_retry_lab_phase("failed", "build_lab")


def test_cannot_retry_lab_phase_from_other_errors_or_build():
    assert not can_retry_lab_phase("error", "build_vpn")
    assert not can_retry_lab_phase("error")
    assert not can_retry_lab_phase("build_lab")
    assert not can_retry_lab_phase("running")
    assert not can_retry_lab_phase("queued")


def test_is_stale_lab_build():
    assert is_stale_lab_build("build_lab", False)
    assert not is_stale_lab_build("build_lab", True)
    assert not is_stale_lab_build("error", False)
    assert not is_stale_lab_build("wait_for_vpn", False)


def test_update_status_clears_error_fields_on_lab_retry(tmp_path):
    config_path = tmp_path / "range.yml"
    config_path.write_text(
        "general:\n  status: error\n  error: playbook failed\n  error_phase: build_lab\n"
    )
    config = {
        "general": {
            "status": "error",
            "error": "playbook failed",
            "error_phase": "build_lab",
        }
    }
    manager = ConfigManager(config, str(config_path), str(tmp_path), _logger())
    manager.update_status("build_lab")

    assert manager.config["general"]["status"] == "build_lab"
    assert "error" not in manager.config["general"]
    assert "error_phase" not in manager.config["general"]

    saved = config_path.read_text()
    assert "error_phase" not in saved
    assert "playbook failed" not in saved
