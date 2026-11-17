"""Export raw events from a Splunk instance in an attack range via the Splunk REST API."""

from __future__ import annotations

from typing import Any

import splunklib.client as client
import splunklib.results as results


SPLUNK_ROLE = "P4T12ICK.ludus_ar_splunk"
DEFAULT_MANAGEMENT_PORT = 8089
DEFAULT_USERNAME = "admin"
DEFAULT_MAX_RESULTS = 10000


class SplunkExportError(Exception):
    """Raised when Splunk export fails."""


def get_splunk_connection_from_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    Resolve Splunk management API connection details from an attack range config.

    :raises ValueError: If no Splunk server/role is configured or IP is missing.
    """
    general = config.get("general") or {}
    attack_range_password = general.get("attack_range_password", "")

    for server in config.get("attack_range") or []:
        if not isinstance(server, dict):
            continue
        ip_last_octet = server.get("ip_last_octet")
        for role in server.get("roles") or []:
            if not isinstance(role, dict):
                continue
            if role.get("role") != SPLUNK_ROLE:
                continue
            if ip_last_octet is None:
                raise ValueError(
                    f"Splunk server '{server.get('name', 'splunk')}' is missing ip_last_octet in config."
                )
            vars_ = role.get("vars") or {}
            password = vars_.get("ludus_ar_splunk_password") or attack_range_password
            if not password:
                raise ValueError("Splunk password not found in config (ludus_ar_splunk_password or attack_range_password).")
            port = vars_.get("ludus_ar_splunk_management_port", DEFAULT_MANAGEMENT_PORT)
            return {
                "host": f"10.0.2.{ip_last_octet}",
                "port": int(port),
                "username": DEFAULT_USERNAME,
                "password": password,
                "scheme": "https",
            }

    raise ValueError(
        "No Splunk server found in attack range configuration. "
        f"Expected a server with role '{SPLUNK_ROLE}'."
    )


def normalize_search(search: str) -> str:
    """Ensure the SPL starts with the search command."""
    query = search.strip()
    if not query:
        raise ValueError("Search query cannot be empty.")
    if not query.lower().startswith("search"):
        query = f"search {query}"
    return query


def connect_splunk(connection: dict[str, Any]) -> client.Service:
    """Connect to Splunk management API (self-signed certs on attack ranges)."""
    try:
        return client.connect(
            host=connection["host"],
            port=connection["port"],
            scheme=connection.get("scheme", "https"),
            username=connection["username"],
            password=connection["password"],
            autologin=True,
            verify=False,
        )
    except Exception as exc:
        raise SplunkExportError(
            f"Failed to connect to Splunk at {connection['scheme']}://{connection['host']}:{connection['port']}: {exc}"
        ) from exc


def export_raw_events(
    config: dict[str, Any],
    *,
    search: str,
    earliest_time: str,
    latest_time: str,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> tuple[list[str], dict[str, Any]]:
    """
    Run a synchronous Splunk export and return the _raw field of each event.

    Uses POST /services/search/jobs/export via splunk-sdk.

    :return: (raw_events, metadata) where each list item is one event's _raw value.
    """
    connection = get_splunk_connection_from_config(config)
    service = connect_splunk(connection)
    query = normalize_search(search)

    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    export_kwargs = {
        "earliest_time": earliest_time,
        "latest_time": latest_time,
        "output_mode": "json",
        "count": max_results,
    }

    raw_events: list[str] = []
    try:
        response = service.jobs.export(query, **export_kwargs)
        reader = results.JSONResultsReader(response)
        for item in reader:
            if isinstance(item, dict):
                raw = item.get("_raw")
                if raw is not None and str(raw).strip():
                    raw_events.append(str(raw))
            elif isinstance(item, results.Message):
                if item.message_type == "FATAL":
                    raise SplunkExportError(item.message or "Splunk export failed.")
    except SplunkExportError:
        raise
    except Exception as exc:
        raise SplunkExportError(f"Splunk search export failed: {exc}") from exc

    metadata = {
        "splunk_host": connection["host"],
        "splunk_port": connection["port"],
        "search": query,
        "earliest_time": earliest_time,
        "latest_time": latest_time,
        "max_results": max_results,
        "event_count": len(raw_events),
    }
    return raw_events, metadata
