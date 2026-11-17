"""Helpers for attack range build status and lab-phase retry."""

from typing import Optional


def can_retry_lab_phase(status: Optional[str], error_phase: Optional[str] = None) -> bool:
    """Return True when the post-VPN lab playbook can be started or retried."""
    normalized_status = (status or "").strip().lower()
    normalized_phase = (error_phase or "").strip().lower()
    if normalized_status == "wait_for_vpn":
        return True
    return normalized_status in ("error", "failed") and normalized_phase == "build_lab"


def is_stale_lab_build(status: Optional[str], thread_alive: bool) -> bool:
    """Return True when status is still build_lab but the lab thread is gone."""
    return (status or "").strip().lower() == "build_lab" and not thread_alive
