"""
Shared utility functions for Attack Range.

This module provides common functionality used by both the CLI and API
for template resolution and config preparation.
"""

import os
import re
import uuid
import yaml
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

_ANSI_ESCAPE_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


def strip_ansi(text: str) -> str:
    """
    Remove ANSI escape sequences from text.

    Subprocess output from tools like Terraform and Ansible may contain
    terminal color codes (e.g., '\\x1b[31m') that are not readable in
    web app logs, structured error messages, or API responses.

    :param text: String that may contain ANSI escape sequences
    :return: String with all ANSI sequences removed
    """
    if not text:
        return text
    return _ANSI_ESCAPE_RE.sub('', text)


def resolve_template_path(template: str, templates_dir: str) -> str:
    """
    Resolve template path from template name or path.
    
    :param template: Template name or path (e.g., 'aws/splunk_minimal_aws', 'templates/aws/splunk_minimal_aws.yml', 'splunk_minimal_aws.yml')
    :param templates_dir: Base directory for templates
    :return: Absolute path to template file
    :raises FileNotFoundError: If template file not found
    """
    template_path = template
    
    # Strip "templates/" prefix if present (for CLI convenience)
    if template_path.startswith("templates/"):
        template_path = template_path[len("templates/"):]
    elif template_path.startswith("templates\\"):  # Windows path
        template_path = template_path[len("templates\\"):]
    
    # If it's a path (contains directory separator) or absolute path, use as-is
    if os.path.sep in template_path or os.path.isabs(template_path):
        # Use the path as provided
        if not os.path.isabs(template_path):
            # Relative path - resolve relative to templates directory
            template_path = os.path.join(templates_dir, template_path)
    else:
        # Simple name - look in templates folder (check all provider subdirs)
        # First try to find it in any provider directory
        for provider in ["aws", "azure", "gcp"]:
            candidate = os.path.join(templates_dir, provider, template)
            if not candidate.endswith('.yml') and not candidate.endswith('.yaml'):
                candidate += '.yml'
            if os.path.exists(candidate):
                return os.path.abspath(candidate)
        
        # If not found in subdirs, try root templates folder
        template_path = os.path.join(templates_dir, template)
    
    # Add .yml extension if not present
    if not template_path.endswith('.yml') and not template_path.endswith('.yaml'):
        template_path += '.yml'
    
    # Check if file exists
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found: {template}")
    
    return os.path.abspath(template_path)


def load_yaml_file(file_path: str) -> Dict[str, Any]:
    """
    Load YAML file and return as dictionary.
    
    :param file_path: Path to YAML file
    :return: Dictionary containing YAML content
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml_file(file_path: str, content: Dict[str, Any]) -> None:
    """
    Save dictionary as YAML file.
    
    :param file_path: Path to save YAML file
    :param content: Dictionary to save as YAML
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(content, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _deep_merge(base: dict, overrides: dict) -> None:
    """Merge overrides into base in-place. Only top-level keys are merged for cloud sections."""
    for key, value in overrides.items():
        if value is None:
            continue
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key].update(value)
        else:
            base[key] = value


def prepare_config_from_template(
    template: str,
    templates_dir: str,
    config_dir: str,
    generate_id: bool = True,
    cloud_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
    general_overrides: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, Any], str, str]:
    """
    Prepare a config from a template by loading it, adding metadata, and saving to config folder.
    
    This function:
    1. Resolves and loads the template
    2. Applies cloud_overrides into the provider section (aws, azure, gcp) if provided
    3. Applies general_overrides into config["general"] if provided (e.g. ip_whitelist, attack_range_password)
    4. Extracts template name and relative path
    5. Generates attack_range_id (if generate_id=True)
    6. Stores template name and path in config's general section
    7. Sets initial status to "queued"
    8. Saves config to config folder
    
    :param template: Template name or path
    :param templates_dir: Base directory for templates
    :param config_dir: Directory to save config files
    :param generate_id: Whether to generate a new attack_range_id (default: True)
    :param cloud_overrides: Optional dict of provider -> { key: value } to merge into config
    :param general_overrides: Optional dict of general keys to merge into config["general"] (e.g. ip_whitelist, attack_range_password)
    :return: Tuple of (config_dict, config_path, attack_range_id)
    """
    # Resolve template path
    template_path = resolve_template_path(template, templates_dir)
    
    # Load template config
    config = load_yaml_file(template_path)
    
    # Apply cloud-specific overrides before saving (e.g. from app build form)
    if cloud_overrides:
        for provider, fields in cloud_overrides.items():
            if not fields:
                continue
            provider_key = provider.lower()
            if provider_key not in config:
                config[provider_key] = {}
            _deep_merge(config[provider_key], fields)
    
    # Apply general overrides (ip_whitelist, attack_range_password, etc.)
    if general_overrides:
        if "general" not in config:
            config["general"] = {}
        _deep_merge(config["general"], general_overrides)
    
    # Extract template name from path (e.g., "aws/splunk_minimal_aws.yml" -> "splunk_minimal_aws.yml")
    template_name = os.path.basename(template_path)
    # Also store relative path like "aws/splunk_minimal_aws.yml"
    relative_template_path = os.path.relpath(template_path, templates_dir)
    
    # Ensure general section exists
    if "general" not in config:
        config["general"] = {}
    
    # Store template name and path in config
    config["general"]["name"] = template_name
    config["general"]["template_path"] = relative_template_path
    
    # Generate or get attack_range_id
    if generate_id:
        attack_range_id = str(uuid.uuid4())
        config["general"]["attack_range_id"] = attack_range_id
    else:
        attack_range_id = config["general"].get("attack_range_id")
        if not attack_range_id:
            raise ValueError("attack_range_id not found in config and generate_id=False")
    
    # Set initial status
    config["general"]["status"] = "queued"
    config["general"]["start_time"] = datetime.now().isoformat()
    
    # Save config to config folder
    config_filename = f"{attack_range_id}.yml"
    config_path = os.path.join(config_dir, config_filename)
    save_yaml_file(config_path, config)
    
    return config, config_path, attack_range_id


def get_wireguard_config(ansible_dir: str, attack_range_id: str, wireguard_config_dir: str) -> Optional[str]:
    """
    Read WireGuard client configuration file.
    
    :param ansible_dir: Directory where Ansible saves the config
    :param attack_range_id: Attack range ID for filename (unused, kept for compatibility)
    :param wireguard_config_dir: Directory to save WireGuard configs (unused, kept for compatibility)
    :return: WireGuard config content or None if not found
    """
    return get_wireguard_config_for_client(ansible_dir, "client1")


def get_wireguard_config_for_client(ansible_dir: str, client_name: str) -> Optional[str]:
    """
    Read WireGuard client configuration file for a specific client.
    
    :param ansible_dir: Directory where Ansible saves the config (client_configs subdir)
    :param client_name: Name of the client (e.g. "client1", "alice")
    :return: WireGuard config content or None if not found
    """
    try:
        source_config_path = os.path.join(ansible_dir, "client_configs", f"{client_name}.conf")
        if os.path.exists(source_config_path):
            with open(source_config_path, 'r') as f:
                return f.read()
    except Exception as e:
        import sys
        print(f"Error reading WireGuard config for {client_name}: {e}", file=sys.stderr)
    return None
