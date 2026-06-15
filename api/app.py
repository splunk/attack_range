"""Flask API for Attack Range Controller with OpenAPI documentation."""

import os
import sys
import time
import glob
import yaml
import threading
import traceback
import subprocess
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List

from flask import jsonify, request
from attack_range.utils import strip_ansi
from flask_openapi3 import OpenAPI, Info, Tag
from flask_cors import CORS
from pydantic import ValidationError

# Add parent directory to path to import attack_range module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from attack_range.attack_range_controller import AttackRangeController
from attack_range.splunk_export import SplunkExportError, export_raw_events
from attack_range.utils import prepare_config_from_template, resolve_template_path, load_yaml_file, save_yaml_file
from api.cloud_fields import get_cloud_fields_schema, get_gcp_zones_for_region
from api.models import (
    HealthResponse,
    BuildRequest,
    BuildResponse,
    DestroyRequest,
    DestroyResponse,
    OperationStatusResponse,
    TemplateInfo,
    ServerInfo,
    TemplateListResponse,
    TemplateContentResponse,
    ConfigInfo,
    ConfigListResponse,
    ConfigContentResponse,
    ErrorResponse,
    AttackRangeIdPath,
    TemplatePath,
    CloudFieldsProviderPath,
    ConfigIdPath,
    AttackRangeListResponse,
    ProviderAvailability,
    ProviderCheckResponse,
    SimulateRequest,
    SimulateResponse,
    SplunkExportRequest,
    SplunkExportResponse,
    ShareRequest,
    ShareResponse,
    UpdateNameRequest,
    UpdateNameResponse,
)

# Disable macOS fork safety warning
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"

# Initialize Flask-OpenAPI3 app
info = Info(
    title="Attack Range API",
    version="1.0.0",
    description="REST API for building and managing Attack Range infrastructure with automated OpenAPI documentation"
)

app = OpenAPI(__name__, info=info)

# Enable CORS for all routes
# Allow requests from localhost (for direct access) and from app container
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:4321", "http://localhost:3000", "http://127.0.0.1:4321", "http://127.0.0.1:3000", "http://app:4321"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Define tags for grouping endpoints
health_tag = Tag(name="Health", description="Health check endpoints")
attack_range_tag = Tag(name="Attack Range", description="Attack range build and destroy operations")
template_tag = Tag(name="Templates", description="Template management endpoints")
config_tag = Tag(name="Configs", description="Configuration management endpoints")
provider_tag = Tag(name="Providers", description="Cloud provider CLI availability endpoints")

# Directory paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
WIREGUARD_CONFIG_DIR = os.path.join(BASE_DIR, "wireguard_config")

# Global state for tracking running operations
running_operations: Dict[str, Dict[str, Any]] = {}
operations_lock = threading.Lock()


def check_cli_available(cli_command: str, version_flag: str = "--version") -> Tuple[bool, Optional[str]]:
    """
    Check if a CLI command is available.
    
    :param cli_command: CLI command name (e.g., 'aws', 'az', 'gcloud')
    :param version_flag: Flag to check version (default: '--version')
    :return: Tuple of (is_available, error_message)
    """
    try:
        # First, try to find the command in PATH
        cmd_path = shutil.which(cli_command)
        if not cmd_path:
            return False, f"CLI command '{cli_command}' not found in PATH"
        
        # Use the full path to the command
        result = subprocess.run(
            [cmd_path, version_flag],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            env=os.environ.copy()
        )
        if result.returncode == 0:
            return True, None
        else:
            # Include stderr in error message if available
            error_msg = f"Command '{cli_command}' returned non-zero exit code: {result.returncode}"
            if result.stderr:
                error_msg += f" - {result.stderr.strip()}"
            return False, error_msg
    except FileNotFoundError:
        return False, f"CLI command '{cli_command}' not found in PATH"
    except subprocess.TimeoutExpired:
        return False, f"CLI command '{cli_command}' timed out"
    except Exception as e:
        return False, f"Error checking CLI '{cli_command}': {str(e)}"


def check_credentials_available(provider: str) -> Tuple[bool, Optional[str]]:
    """
    Check if credentials are available for a cloud provider.
    
    :param provider: Provider name ('aws', 'azure', 'gcp')
    :return: Tuple of (has_credentials, error_message)
    """
    try:
        if provider.lower() == "aws":
            # Check for AWS credentials
            aws_creds_path = os.path.expanduser("~/.aws/credentials")
            aws_config_path = os.path.expanduser("~/.aws/config")
            if os.path.exists(aws_creds_path) or os.path.exists(aws_config_path):
                # Also check if AWS CLI can authenticate
                aws_cmd = shutil.which("aws")
                if not aws_cmd:
                    return False, "AWS CLI not found in PATH"
                
                result = subprocess.run(
                    [aws_cmd, "sts", "get-caller-identity"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                    env=os.environ.copy()
                )
                if result.returncode == 0:
                    return True, None
                else:
                    error_msg = "AWS credentials found but authentication failed"
                    if result.stderr:
                        error_msg += f": {result.stderr.strip()}"
                    return False, error_msg
            return False, "AWS credentials not found (~/.aws/credentials or ~/.aws/config)"
        
        elif provider.lower() == "azure":
            # Check for Azure credentials
            azure_config_path = os.path.expanduser("~/.azure")
            if os.path.exists(azure_config_path):
                # Check if Azure CLI can authenticate
                az_cmd = shutil.which("az")
                if not az_cmd:
                    return False, "Azure CLI not found in PATH"
                
                result = subprocess.run(
                    [az_cmd, "account", "show"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                    env=os.environ.copy()
                )
                if result.returncode == 0:
                    return True, None
                else:
                    error_msg = "Azure credentials found but authentication failed"
                    if result.stderr:
                        error_msg += f": {result.stderr.strip()}"
                    return False, error_msg
            return False, "Azure credentials not found (~/.azure)"
        
        elif provider.lower() == "gcp":
            # Check for GCP credentials
            gcp_config_path = os.path.expanduser("~/.config/gcloud")
            if os.path.exists(gcp_config_path):
                # Check if gcloud can authenticate
                gcloud_cmd = shutil.which("gcloud")
                if not gcloud_cmd:
                    return False, "GCP CLI not found in PATH"
                
                # Check for active accounts (case-insensitive)
                result = subprocess.run(
                    [gcloud_cmd, "auth", "list"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                    env=os.environ.copy()
                )
                
                if result.returncode != 0:
                    error_msg = f"Failed to check GCP authentication: {result.stderr.strip() if result.stderr else 'Unknown error'}"
                    return False, error_msg
                
                # Check for ACTIVE in output (case-insensitive)
                stdout_upper = result.stdout.upper()
                if "ACTIVE" in stdout_upper or "*" in result.stdout:
                    # Verify we can actually use the credentials by checking project
                    project_result = subprocess.run(
                        [gcloud_cmd, "config", "get-value", "project"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        check=False,
                        env=os.environ.copy()
                    )
                    if project_result.returncode == 0:
                        return True, None
                    # If project check fails, still consider it available if auth list shows active
                    # (project might not be set but auth is valid)
                    if "ACTIVE" in stdout_upper:
                        return True, None
                
                # No active authentication found
                error_msg = "GCP credentials found but no active authentication"
                if result.stdout:
                    # Include a snippet of the auth list output for debugging
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 0:
                        error_msg += f" (found {len([l for l in lines if l.strip() and not l.startswith('Credentialed')])} account(s))"
                return False, error_msg
            return False, "GCP credentials not found (~/.config/gcloud)"
        
        return False, f"Unknown provider: {provider}"
    except Exception as e:
        return False, f"Error checking credentials for {provider}: {str(e)}"


def get_provider_availability(test_missing: Optional[str] = None) -> list:
    """
    Get availability status for all cloud providers.
    This implementation no longer checks local CLI installation or credentials;
    all providers are treated as available (unless simulated as missing for tests).
    
    :param test_missing: Optional provider name to simulate as missing (for testing)
    :return: List of ProviderAvailability objects
    """
    providers_config = [
        {"provider": "aws", "cli": "aws"},
        {"provider": "azure", "cli": "az"},
        {"provider": "gcp", "cli": "gcloud"},
    ]

    results = []
    for provider_config in providers_config:
        provider = provider_config["provider"]
        cli_command = provider_config["cli"]

        # If testing missing provider, simulate it as unavailable
        if test_missing and test_missing.lower() == provider.lower():
            results.append(
                ProviderAvailability(
                    provider=provider,
                    available=False,
                    cli_command=cli_command,
                    error_message=f"Simulated missing CLI for testing (test_missing={test_missing})",
                )
            )
        else:
            # Treat provider as available without performing any local CLI/credential checks
            results.append(
                ProviderAvailability(
                    provider=provider,
                    available=True,
                    cli_command=cli_command,
                    error_message=None,
                )
            )

    return results


def get_templates() -> list:
    """Get list of all available templates."""
    templates = []
    if not os.path.exists(TEMPLATES_DIR):
        return templates

    # Scan templates directory
    for provider in ["aws", "azure", "gcp"]:
        provider_dir = os.path.join(TEMPLATES_DIR, provider)
        if os.path.exists(provider_dir):
            yml_files = glob.glob(os.path.join(provider_dir, "*.yml"))
            for yml_file in yml_files:
                # Load template to get description and architecture
                description = None
                architecture = None
                try:
                    template_content = load_yaml_file(yml_file)
                    if template_content:
                        general = template_content.get("general")
                        if general and isinstance(general, dict):
                            description = general.get("description")
                        
                        # Extract architecture information
                        attack_range = template_content.get("attack_range")
                        if attack_range and isinstance(attack_range, list):
                            servers = []
                            for server in attack_range:
                                if isinstance(server, dict):
                                    # Determine OS type
                                    os_type = None
                                    if server.get("linux"):
                                        os_type = "linux"
                                    elif server.get("windows"):
                                        os_type = "windows"
                                    
                                    # Extract role names
                                    roles = []
                                    server_roles = server.get("roles", [])
                                    if isinstance(server_roles, list):
                                        for role in server_roles:
                                            if isinstance(role, dict):
                                                role_name = role.get("role")
                                                if role_name:
                                                    roles.append(role_name)
                                            elif isinstance(role, str):
                                                roles.append(role)
                                    
                                    servers.append(ServerInfo(
                                        name=server.get("name", ""),
                                        instance_type=server.get("instance_type"),
                                        ip_last_octet=server.get("ip_last_octet"),
                                        os_type=os_type,
                                        roles=roles if roles else None,
                                        zeek=server.get("zeek"),
                                        zeek_monitor=server.get("zeek_monitor")
                                    ))
                            architecture = servers if servers else None
                except Exception as e:
                    # If loading fails, continue without description/architecture
                    # Log error for debugging
                    import sys
                    print(f"Warning: Failed to load template from {yml_file}: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc()
                
                templates.append(TemplateInfo(
                    name=os.path.basename(yml_file),
                    provider=provider,
                    path=yml_file,
                    description=description,
                    architecture=architecture
                ))
    
    return templates


# Note: load_yaml_file, save_yaml_file, and resolve_template_path are now imported from attack_range.utils


# Note: get_wireguard_config and update_config_status are now handled by the controller


def get_config_path_from_attack_range_id(attack_range_id: str) -> Optional[str]:
    """Get config file path from attack_range_id."""
    config_filename = f"{attack_range_id}.yml"
    config_path = os.path.join(CONFIG_DIR, config_filename)
    if os.path.exists(config_path):
        return config_path
    return None


def _write_config_error_status(config_path: str, error: str, error_phase: str) -> None:
    """Write error status into the config file without using the controller (e.g. when controller init fails)."""
    try:
        if not config_path or not os.path.exists(config_path):
            return
        config = load_yaml_file(config_path)
        if "general" not in config:
            config["general"] = {}
        config["general"]["status"] = "error"
        config["general"]["error"] = error
        config["general"]["error_phase"] = error_phase
        config["general"]["end_time"] = datetime.now().isoformat()
        save_yaml_file(config_path, config)
    except Exception:
        pass


def _wait_abort_then_destroy(attack_range_id: str, config_path: str) -> None:
    """Wait for build to stop (abort or error), then run destroy. Used when user clicks Destroy during build."""
    build_statuses = ("queued", "build_vpn", "build_lab")
    for _ in range(45):
        time.sleep(2)
        with operations_lock:
            cur = running_operations.get(attack_range_id)
            s = (cur.get("status") if cur else None) or ""
        if not s and config_path and os.path.exists(config_path):
            try:
                cfg = load_yaml_file(config_path)
                s = cfg.get("general", {}).get("status") or ""
            except Exception:
                s = ""
        if s not in build_statuses:
            break
    if not os.path.exists(config_path):
        return
    try:
        config = load_yaml_file(config_path)
        with operations_lock:
            running_operations[attack_range_id] = {
                "type": "destroy",
                "status": "queued",
                "created_time": datetime.now().isoformat(),
                "attack_range_id": attack_range_id
            }
        # Pass current status (e.g. aborted/error) so we clear the range on destroy failure
        run_destroy_operation(config, config_path, attack_range_id, previous_status=s or "")
    except Exception:
        pass


def _check_abort_and_set_aborted(attack_range_id: str, config_path: Optional[str] = None) -> bool:
    """If abort_requested is set for this attack_range_id, set status to aborted and return True. Else return False."""
    with operations_lock:
        op = running_operations.get(attack_range_id)
        if not op or not op.get("abort_requested"):
            return False
        running_operations[attack_range_id]["status"] = "aborted"
        running_operations[attack_range_id]["end_time"] = datetime.now().isoformat()
        path = config_path or op.get("config_path") or get_config_path_from_attack_range_id(attack_range_id)
    if path and os.path.exists(path):
        try:
            config = load_yaml_file(path)
            if "general" not in config:
                config["general"] = {}
            config["general"]["status"] = "aborted"
            config["general"]["end_time"] = datetime.now().isoformat()
            save_yaml_file(path, config)
        except Exception:
            pass
    return True


def run_build_vpn_phase(config: Dict[str, Any], config_path: str, attack_range_id: str):
    """Run phase 1: Build VPN infrastructure (up to VPN config generation)."""
    try:
        if _check_abort_and_set_aborted(attack_range_id, config_path):
            return
        with operations_lock:
            running_operations[attack_range_id]["status"] = "build_vpn"
            running_operations[attack_range_id]["start_time"] = datetime.now().isoformat()

        # Create controller with config
        controller = AttackRangeController(config, config_path=config_path)

        # Build VPN phase (handles all steps including status updates; checks abort between steps)
        router_public_ip, wireguard_config = controller.build_vpn_phase(attack_range_id, abort_check=lambda: _check_abort_and_set_aborted(attack_range_id, config_path))
        
        wireguard_config_path = os.path.join(WIREGUARD_CONFIG_DIR, f"{attack_range_id}.conf")
        
        # Update operation status
        with operations_lock:
            running_operations[attack_range_id]["status"] = "wait_for_vpn"
            running_operations[attack_range_id]["attack_range_id"] = attack_range_id
            running_operations[attack_range_id]["router_public_ip"] = router_public_ip
            running_operations[attack_range_id]["wireguard_config"] = wireguard_config
            running_operations[attack_range_id]["wireguard_config_path"] = wireguard_config_path
            running_operations[attack_range_id]["config_path"] = config_path
            
    except Exception as e:
        is_aborted = "Build aborted" in str(e)
        if not is_aborted:
            with operations_lock:
                running_operations[attack_range_id]["status"] = "error"
                running_operations[attack_range_id]["end_time"] = datetime.now().isoformat()
                running_operations[attack_range_id]["error"] = strip_ansi(str(e))
                running_operations[attack_range_id]["error_phase"] = "build_vpn"
                running_operations[attack_range_id]["traceback"] = strip_ansi(traceback.format_exc())

            # Update error status in config file (via controller if available, else direct write)
            try:
                controller = AttackRangeController(config, config_path=config_path)
                controller.config_manager.update_status("error", error=strip_ansi(str(e)), error_phase="build_vpn")
            except Exception:
                _write_config_error_status(config_path, strip_ansi(str(e)), "build_vpn")


def run_build_lab_phase(attack_range_id: str):
    """Run phase 2: Build lab infrastructure (after VPN connection)."""
    try:
        # Get config path from running_operations or from config file
        with operations_lock:
            config_path = running_operations[attack_range_id].get("config_path")
            if not config_path:
                config_path = get_config_path_from_attack_range_id(attack_range_id)
            running_operations[attack_range_id]["status"] = "build_lab"
            if config_path:
                running_operations[attack_range_id]["config_path"] = config_path
        
        if not config_path or not os.path.exists(config_path):
            raise Exception("Config file not found for attack range")
        
        # Load config
        config = load_yaml_file(config_path)
        controller = AttackRangeController(config, config_path=config_path)

        abort_check = lambda: _check_abort_and_set_aborted(attack_range_id, config_path)

        # Build lab phase (handles all steps including status updates)
        controller.build_lab_phase(attack_range_id, abort_check=abort_check)

        # Get router public IP
        router_public_ip = controller.terraform_manager.get_output("router_public_ip")
        
        # Update operation status
        with operations_lock:
            running_operations[attack_range_id]["status"] = "running"
            running_operations[attack_range_id]["end_time"] = datetime.now().isoformat()
            running_operations[attack_range_id]["result"] = {
                "attack_range_id": attack_range_id,
                "router_public_ip": router_public_ip,
                "config_file": config_path
            }
            
    except Exception as e:
        is_aborted = "Build aborted" in str(e)
        config_path = None
        if not is_aborted:
            with operations_lock:
                config_path = running_operations[attack_range_id].get("config_path")
                if not config_path:
                    config_path = get_config_path_from_attack_range_id(attack_range_id)
                running_operations[attack_range_id]["status"] = "error"
                running_operations[attack_range_id]["end_time"] = datetime.now().isoformat()
                running_operations[attack_range_id]["error"] = strip_ansi(str(e))
                running_operations[attack_range_id]["error_phase"] = "build_lab"
                running_operations[attack_range_id]["traceback"] = strip_ansi(traceback.format_exc())

            # Update error status in config file (via controller if available, else direct write)
            if config_path:
                try:
                    config = load_yaml_file(config_path)
                    controller = AttackRangeController(config, config_path=config_path)
                    controller.config_manager.update_status("error", error=strip_ansi(str(e)), error_phase="build_lab")
                except Exception:
                    _write_config_error_status(config_path, strip_ansi(str(e)), "build_lab")


def run_destroy_operation(
    config: Dict[str, Any],
    config_path: Optional[str],
    attack_range_id: str,
    previous_status: str = "",
):
    """Run destroy operation in a separate thread. When previous_status is 'error' or 'failed', we still remove the config on destroy failure so the range is cleared."""
    controller = None
    try:
        with operations_lock:
            running_operations[attack_range_id]["status"] = "destroying"
            running_operations[attack_range_id]["start_time"] = datetime.now().isoformat()

        if config_path:
            try:
                controller = AttackRangeController(config, config_path=config_path)
                controller.config_manager.update_status("destroying")
            except Exception:
                pass

        if not controller:
            controller = AttackRangeController(config, config_path=config_path)
        controller.destroy()

        if config_path and os.path.exists(config_path):
            try:
                os.remove(config_path)
            except Exception as e:
                controller.logger.warning(f"Failed to delete config file: {e}")

        with operations_lock:
            if attack_range_id in running_operations:
                del running_operations[attack_range_id]
    except Exception as e:
        with operations_lock:
            running_operations[attack_range_id]["status"] = "failed"
            running_operations[attack_range_id]["end_time"] = datetime.now().isoformat()
            running_operations[attack_range_id]["error"] = strip_ansi(str(e))
            running_operations[attack_range_id]["traceback"] = strip_ansi(traceback.format_exc())

        if config_path:
            try:
                c = AttackRangeController(config, config_path=config_path)
                c.config_manager.update_status("failed", error=strip_ansi(str(e)))
            except Exception:
                pass

        # If this was already a failed/errored/aborted range (e.g. build_vpn error), clear it so user can start fresh
        if previous_status in ("error", "failed", "aborted") and config_path and os.path.exists(config_path):
            try:
                os.remove(config_path)
                with operations_lock:
                    if attack_range_id in running_operations:
                        del running_operations[attack_range_id]
            except Exception:
                pass


# ============================================================================
# HEALTH ENDPOINTS
# ============================================================================

@app.get(
    "/health",
    tags=[health_tag],
    responses={200: HealthResponse},
    summary="Health check",
    description="Check if the API is running and healthy"
)
def health():
    """Health check endpoint."""
    return jsonify(HealthResponse(status="healthy", version="1.0.0").model_dump())


# ============================================================================
# ATTACK RANGE ENDPOINTS
# ============================================================================

@app.post(
    "/attack-range/build",
    tags=[attack_range_tag],
    responses={202: BuildResponse, 400: ErrorResponse, 404: ErrorResponse, 500: ErrorResponse},
    summary="Build attack range",
    description="Build a new attack range (provide 'template') OR continue existing build after VPN connection (provide 'attack_range_id'). This is an asynchronous operation."
)
def build_attack_range(body: BuildRequest):
    """Build a new attack range or continue existing build."""
    try:
        import uuid
        
        # Determine if this is a new build or continuation
        is_continuation = body.attack_range_id is not None
        is_new_build = body.template is not None
        
        # Validate input: must provide either template (new build) or attack_range_id (continuation)
        if not is_new_build and not is_continuation:
            return jsonify(ErrorResponse(
                message="Either 'template' (for new build) or 'attack_range_id' (to continue after VPN) must be provided"
            ).model_dump()), 400
        
        if is_new_build and is_continuation:
            return jsonify(ErrorResponse(
                message="Cannot provide both 'template' and 'attack_range_id'. Use 'template' for new builds or 'attack_range_id' to continue."
            ).model_dump()), 400
        
        # Handle continuation (Phase 2: Lab build after VPN connection)
        if is_continuation:
            attack_range_id = body.attack_range_id
            
            # Check status from running_operations or config file
            status = None
            config_path = None
            
            with operations_lock:
                if attack_range_id in running_operations:
                    status = running_operations[attack_range_id].get("status")
                    config_path = running_operations[attack_range_id].get("config_path")
            
            # If not in running_operations, check config file
            if not status:
                config_path = get_config_path_from_attack_range_id(attack_range_id)
                if config_path:
                    operation = load_operation_from_config(config_path)
                    if operation:
                        status = operation.get("status")
                        # Update running_operations with info from config
                        with operations_lock:
                            if attack_range_id not in running_operations:
                                running_operations[attack_range_id] = operation
                                running_operations[attack_range_id]["config_path"] = config_path
            
            if not status:
                return jsonify(ErrorResponse(
                    message=f"No build found for attack_range_id: {attack_range_id}",
                    details="Make sure you started a build first"
                ).model_dump()), 404
            
            if status != "wait_for_vpn":
                return jsonify(ErrorResponse(
                    message=f"Build is not waiting for VPN connection. Current status: {status}",
                    details="The attack range must be in 'wait_for_vpn' status to continue"
                ).model_dump()), 400
            
            # Ensure config_path is set in running_operations
            if config_path:
                with operations_lock:
                    if attack_range_id in running_operations:
                        running_operations[attack_range_id]["config_path"] = config_path
            
            # Start phase 2 in a separate thread
            thread = threading.Thread(
                target=run_build_lab_phase,
                args=(attack_range_id,)
            )
            thread.daemon = True
            thread.start()
            
            return jsonify(BuildResponse(
                status="accepted",
                message=f"Continuing build (lab phase) for attack range: {attack_range_id}",
                attack_range_id=attack_range_id,
                phase="lab"
            ).model_dump()), 202
        
        # Handle new build (Phase 1: VPN setup)
        else:
            # Prepare config from template using shared utility
            try:
                config, config_path, attack_range_id = prepare_config_from_template(
                    body.template,
                    TEMPLATES_DIR,
                    CONFIG_DIR,
                    generate_id=True,
                    cloud_overrides=body.cloud_overrides,
                    general_overrides=body.general_overrides
                )
                
                # Extract template name from config (already set by prepare_config_from_template)
                template_name = config.get("general", {}).get("name")
                
            except FileNotFoundError as e:
                return jsonify(ErrorResponse(
                    message="Template not found",
                    details=str(e)
                ).model_dump()), 404
            except Exception as e:
                return jsonify(ErrorResponse(
                    message="Failed to prepare config from template",
                    details=str(e)
                ).model_dump()), 500
            
            # Initialize operation state (keyed by attack_range_id)
            with operations_lock:
                running_operations[attack_range_id] = {
                    "type": "build",
                    "status": "queued",
                    "created_time": datetime.now().isoformat(),
                    "attack_range_id": attack_range_id,
                    "template_name": template_name
                }
            
            # Status is already set to "queued" by prepare_config_from_template
            
            # Start phase 1 in a separate thread
            thread = threading.Thread(
                target=run_build_vpn_phase,
                args=(config, config_path, attack_range_id)
            )
            thread.daemon = True
            thread.start()
            
            return jsonify(BuildResponse(
                status="accepted",
                message=f"Build operation started (VPN phase). Attack Range ID: {attack_range_id}",
                attack_range_id=attack_range_id,
                phase="vpn"
            ).model_dump()), 202
        
    except Exception as e:
        return jsonify(ErrorResponse(
            message="Failed to start build operation",
            details=str(e)
        ).model_dump()), 500


@app.post(
    "/attack-range/destroy",
    tags=[attack_range_tag],
    responses={202: DestroyResponse, 400: ErrorResponse, 404: ErrorResponse, 500: ErrorResponse},
    summary="Destroy attack range",
    description="Destroy an existing attack range infrastructure by attack_range_id."
)
def destroy_attack_range(body: DestroyRequest):
    """Destroy an attack range. If a build is in progress, requests abort and waits for it to stop, then runs destroy."""
    try:
        attack_range_id = body.attack_range_id

        config_filename = f"{attack_range_id}.yml" if not attack_range_id.endswith('.yml') else attack_range_id
        config_path = os.path.join(CONFIG_DIR, config_filename)

        if not os.path.exists(config_path):
            return jsonify(ErrorResponse(
                message=f"Config file not found for attack_range_id: {attack_range_id}",
                details="Make sure the attack range exists"
            ).model_dump()), 404

        # If a build is in progress, request abort and run "wait for abort then destroy" in a thread
        build_statuses = ("queued", "build_vpn", "build_lab")
        with operations_lock:
            current = running_operations.get(attack_range_id)
            status = (current.get("status") if current else None) or ""
        if not status and os.path.exists(config_path):
            config_for_status = load_yaml_file(config_path)
            status = config_for_status.get("general", {}).get("status") or ""

        if status in build_statuses:
            with operations_lock:
                op = running_operations.get(attack_range_id)
                if op:
                    op["abort_requested"] = True
            # Run wait-for-abort-then-destroy in background; return 202 immediately
            thread = threading.Thread(
                target=_wait_abort_then_destroy,
                args=(attack_range_id, config_path)
            )
            thread.daemon = True
            thread.start()
            return jsonify(DestroyResponse(
                status="accepted",
                message=f"Build abort requested; destroy will run when build stops. Attack Range ID: {attack_range_id}"
            ).model_dump()), 202

        # Remember if we're cleaning up an already-failed/errored range (so we can clear it even when destroy fails)
        previous_status = status.strip().lower() if status else ""
        config = load_yaml_file(config_path)

        config_attack_range_id = config.get("general", {}).get("attack_range_id")
        if config_attack_range_id and config_attack_range_id != attack_range_id:
            return jsonify(ErrorResponse(
                message=f"attack_range_id mismatch. Expected: {attack_range_id}, Found in config: {config_attack_range_id}"
            ).model_dump()), 400

        with operations_lock:
            running_operations[attack_range_id] = {
                "type": "destroy",
                "status": "queued",
                "created_time": datetime.now().isoformat(),
                "attack_range_id": attack_range_id
            }

        try:
            controller = AttackRangeController(config, config_path=config_path)
            controller.config_manager.update_status("destroying")
        except Exception:
            pass

        thread = threading.Thread(
            target=run_destroy_operation,
            args=(config, config_path, attack_range_id, previous_status)
        )
        thread.daemon = True
        thread.start()

        return jsonify(DestroyResponse(
            status="accepted",
            message=f"Destroy operation started. Attack Range ID: {attack_range_id}"
        ).model_dump()), 202
        
    except Exception as e:
        return jsonify(ErrorResponse(
            message="Failed to start destroy operation",
            details=str(e)
        ).model_dump()), 500


@app.post(
    "/attack-range/abort",
    tags=[attack_range_tag],
    responses={200: DestroyResponse, 400: ErrorResponse, 404: ErrorResponse, 500: ErrorResponse},
    summary="Abort attack range build",
    description="Abort a build operation in progress. Sets status to 'aborted'."
)
def abort_attack_range(body: DestroyRequest):
    """Abort a build operation by setting abort_requested flag and status to aborted."""
    try:
        attack_range_id = body.attack_range_id

        config_filename = f"{attack_range_id}.yml" if not attack_range_id.endswith('.yml') else attack_range_id
        config_path = os.path.join(CONFIG_DIR, config_filename)

        if not os.path.exists(config_path):
            return jsonify(ErrorResponse(
                message=f"Config file not found for attack_range_id: {attack_range_id}",
                details="Make sure the attack range exists"
            ).model_dump()), 404

        # Check if build is in progress
        build_statuses = ("queued", "build_vpn", "build_lab")
        with operations_lock:
            current = running_operations.get(attack_range_id)
            status = (current.get("status") if current else None) or ""
        
        if not status and os.path.exists(config_path):
            try:
                config_for_status = load_yaml_file(config_path)
                status = config_for_status.get("general", {}).get("status") or ""
            except Exception:
                status = ""

        if status not in build_statuses:
            return jsonify(ErrorResponse(
                message=f"Cannot abort: attack range is not in a build state. Current status: {status}",
                details="Abort can only be called during build (queued, build_vpn, build_lab)"
            ).model_dump()), 400

        # Set abort_requested flag
        with operations_lock:
            op = running_operations.get(attack_range_id)
            if op:
                op["abort_requested"] = True
            else:
                # If not in running_operations, create entry
                running_operations[attack_range_id] = {
                    "type": "build",
                    "status": status,
                    "abort_requested": True,
                    "attack_range_id": attack_range_id
                }

        # Immediately set status to aborted
        _check_abort_and_set_aborted(attack_range_id, config_path)

        return jsonify(DestroyResponse(
            status="accepted",
            message=f"Build abort requested. Attack Range ID: {attack_range_id}"
        ).model_dump()), 200
        
    except Exception as e:
        return jsonify(ErrorResponse(
            message="Failed to abort build operation",
            details=str(e)
        ).model_dump()), 500


@app.get(
    "/attack-range/status/<attack_range_id>",
    tags=[attack_range_tag],
    responses={200: OperationStatusResponse, 404: ErrorResponse},
    summary="Get attack range status",
    description="Get the status of a build or destroy operation by attack_range_id"
)
def get_attack_range_status(path: AttackRangeIdPath):
    """Get status of an attack range operation."""
    attack_range_id = path.attack_range_id
    
    operation = None
    config_path = get_config_path_from_attack_range_id(attack_range_id)
    
    # First check running_operations
    with operations_lock:
        if attack_range_id in running_operations:
            operation = running_operations[attack_range_id].copy()
            operation["attack_range_id"] = attack_range_id
    
    # If config file exists, prioritize status from config file over running_operations
    if config_path and os.path.exists(config_path):
        config_content = load_yaml_file(config_path)
        if config_content:
            general = config_content.get("general", {})
            config_status = general.get("status")
            if config_status and operation:
                # Config file is source of truth for status
                operation["status"] = config_status
            # Merge sharing from config (e.g. after a share) when available
            if operation and general.get("sharing") and isinstance(general.get("sharing"), dict):
                operation["sharing"] = general["sharing"]
            # Load attack_range_name from config
            if operation:
                attack_range_name = general.get("attack_range_name")
                if attack_range_name:
                    operation["attack_range_name"] = attack_range_name
    
    # If not in running_operations, try to load from config file
    if not operation:
        if config_path:
            operation = load_operation_from_config(config_path)
    
    if not operation:
        return jsonify(ErrorResponse(
            message=f"Attack range not found: {attack_range_id}"
        ).model_dump()), 404
    
    # If running and has config_file, load architecture and Guacamole info
    # This ensures architecture and guacamole_info are loaded even when operation is in running_operations
    if operation.get("status") == "running" and config_path and os.path.exists(config_path):
        architecture = load_architecture_from_config(config_path)
        if architecture:
            if "result" not in operation:
                operation["result"] = {}
            operation["result"]["architecture"] = architecture
        
        # Load Guacamole info
        guacamole_info = load_guacamole_info_from_config(config_path)
        if guacamole_info:
            if "result" not in operation:
                operation["result"] = {}
            operation["result"]["guacamole_info"] = guacamole_info

        # Load default credentials (splunk, soar, guacamole usernames/passwords from config)
        default_credentials = load_default_credentials_from_config(config_path)
        if default_credentials:
            if "result" not in operation:
                operation["result"] = {}
            operation["result"]["default_credentials"] = default_credentials
        
        # Ensure config_file is set in result if not already present
        if "result" in operation and "config_file" not in operation["result"]:
            operation["result"]["config_file"] = config_path
    
    # Validate and return as OperationStatusResponse
    return jsonify(OperationStatusResponse(**operation).model_dump()), 200


def load_guacamole_info_from_config(config_path: str) -> Optional[Dict[str, Any]]:
    """Load Guacamole configuration information from a config file."""
    try:
        config_content = load_yaml_file(config_path)
        if config_content:
            attack_range = config_content.get("attack_range")
            if attack_range and isinstance(attack_range, list):
                for server in attack_range:
                    if isinstance(server, dict):
                        server_roles = server.get("roles", [])
                        if isinstance(server_roles, list):
                            for role in server_roles:
                                if isinstance(role, dict):
                                    role_name = role.get("role")
                                    # Check if this server has the Guacamole role
                                    if role_name == "P4T12ICK.ar_guacamole":
                                        role_vars = role.get("vars", {})
                                        guacamole_servers = role_vars.get("ar_guacamole_servers", [])
                                        
                                        if guacamole_servers:
                                            # Get the IP of the server hosting Guacamole
                                            ip_last_octet = server.get("ip_last_octet")
                                            if ip_last_octet is not None:
                                                host_ip = f"10.0.2.{ip_last_octet}"
                                                
                                                # Extract server information
                                                servers_list = []
                                                for guac_server in guacamole_servers:
                                                    if isinstance(guac_server, dict):
                                                        server_info = {
                                                            "name": guac_server.get("name", ""),
                                                            "protocol": guac_server.get("protocol", ""),
                                                            "hostname": guac_server.get("hostname", ""),
                                                            "port": guac_server.get("port")
                                                        }
                                                        # Include username and password if available (needed for quickconnect)
                                                        if guac_server.get("username"):
                                                            server_info["username"] = guac_server.get("username")
                                                        if guac_server.get("password"):
                                                            server_info["password"] = guac_server.get("password")
                                                        servers_list.append(server_info)
                                                
                                                if servers_list:
                                                    return {
                                                        "host_ip": host_ip,
                                                        "servers": servers_list
                                                    }
    except Exception as e:
        # If loading fails, return None
        import sys
        print(f"Warning: Failed to load Guacamole info from {config_path}: {e}", file=sys.stderr)
    return None


def load_default_credentials_from_config(config_path: str) -> Optional[List[Dict[str, Any]]]:
    """Load default usernames and passwords from config:
    - Splunk, SOAR, Guacamole: fixed usernames, passwords from role vars or general.attack_range_password.
    - Linux: SSH with user_name from config, password from general.attack_range_password.
    - Windows: RDP with user_name from config, password from general.attack_range_password.
    """
    seen = set()
    credentials = []
    try:
        config_content = load_yaml_file(config_path)
        if not config_content:
            return None
        general = config_content.get("general", {})
        attack_range_password = general.get("attack_range_password", "")
        attack_range = config_content.get("attack_range") or []

        for server in attack_range:
            if not isinstance(server, dict):
                continue
            name = server.get("name", "")

            # SSH for Linux servers: user_name from config, default ubuntu.
            # Treat as Linux when linux: true or when windows is not explicitly true (common when only linux is set).
            if server.get("linux") or not server.get("windows"):
                un = server.get("user_name") or "ubuntu"
                credentials.append({"service": "SSH", "server": name, "username": un, "password": attack_range_password})

            # RDP for Windows servers: user_name from config, default Administrator
            if server.get("windows"):
                un = server.get("user_name") or "Administrator"
                credentials.append({"service": "RDP", "server": name, "username": un, "password": attack_range_password})

            for role in server.get("roles") or []:
                if not isinstance(role, dict):
                    continue
                role_name = role.get("role")
                vars_ = role.get("vars") or {}

                if role_name == "P4T12ICK.ludus_ar_splunk" and "splunk" not in seen:
                    seen.add("splunk")
                    pw = vars_.get("ludus_ar_splunk_password") or attack_range_password
                    credentials.append({"service": "splunk", "username": "admin", "password": pw})
                elif role_name == "P4T12ICK.ar_soar" and "soar" not in seen:
                    seen.add("soar")
                    pw = vars_.get("ar_soar_password") or attack_range_password
                    credentials.append({"service": "soar", "username": "soar_local_admin", "password": pw})
                elif role_name == "P4T12ICK.ar_guacamole" and "guacamole" not in seen:
                    seen.add("guacamole")
                    pw = vars_.get("ar_guacamole_password") or attack_range_password
                    credentials.append({"service": "guacamole", "username": "admin", "password": pw})

        return credentials if credentials else None
    except Exception as e:
        import sys
        print(f"Warning: Failed to load default credentials from {config_path}: {e}", file=sys.stderr)
    return None


def load_architecture_from_config(config_path: str) -> Optional[List[Dict[str, Any]]]:
    """Load architecture information from a config file."""
    try:
        config_content = load_yaml_file(config_path)
        if config_content:
            attack_range = config_content.get("attack_range")
            if attack_range and isinstance(attack_range, list):
                servers = []
                for server in attack_range:
                    if isinstance(server, dict):
                        # Determine OS type
                        os_type = None
                        if server.get("linux"):
                            os_type = "linux"
                        elif server.get("windows"):
                            os_type = "windows"
                        
                        # Extract role names
                        roles = []
                        server_roles = server.get("roles", [])
                        if isinstance(server_roles, list):
                            for role in server_roles:
                                if isinstance(role, dict):
                                    role_name = role.get("role")
                                    if role_name:
                                        roles.append(role_name)
                                elif isinstance(role, str):
                                    roles.append(role)
                        
                        servers.append({
                            "name": server.get("name", ""),
                            "instance_type": server.get("instance_type"),
                            "ip_last_octet": server.get("ip_last_octet"),
                            "os_type": os_type,
                            "roles": roles if roles else None,
                            "zeek": server.get("zeek"),
                            "zeek_monitor": server.get("zeek_monitor")
                        })
                
                return servers if servers else None
    except Exception as e:
        # If loading fails, return None
        import sys
        print(f"Warning: Failed to load architecture from {config_path}: {e}", file=sys.stderr)
    return None


def load_operation_from_config(config_path: str) -> Optional[Dict[str, Any]]:
    """Load operation status and metadata from a config file."""
    try:
        config_content = load_yaml_file(config_path)
        if not config_content:
            return None
        
        general = config_content.get("general", {})
        attack_range_id = general.get("attack_range_id")
        if not attack_range_id:
            # Try to get from filename
            attack_range_id = os.path.splitext(os.path.basename(config_path))[0]
        
        # Get status from config, default to "running" if not set
        status = general.get("status", "running")
        
        # Get template name from config (stored as general.name)
        template_name = general.get("name")
        
        # Get attack range name from config (stored as general.attack_range_name)
        attack_range_name = general.get("attack_range_name")
        
        # Build operation dict
        operation_dict = {
            "type": "build",
            "status": status,
            "created_time": datetime.fromtimestamp(os.path.getmtime(config_path)).isoformat(),
            "attack_range_id": attack_range_id,
        }
        
        # Add template name if available
        if template_name:
            operation_dict["template_name"] = template_name
        
        # Add attack range name if available
        if attack_range_name:
            operation_dict["attack_range_name"] = attack_range_name
        
        # Add timestamps if available
        if general.get("start_time"):
            operation_dict["start_time"] = general["start_time"]
        if general.get("end_time"):
            operation_dict["end_time"] = general["end_time"]
        
        # Add router_public_ip if available
        router_public_ip = general.get("router_public_ip")
        if router_public_ip:
            operation_dict["router_public_ip"] = router_public_ip
        
        # Add error info if available
        if general.get("error"):
            operation_dict["error"] = general["error"]
        if general.get("error_phase"):
            operation_dict["error_phase"] = general["error_phase"]
        
        # Build result dict
        result = {
            "attack_range_id": attack_range_id,
            "config_file": config_path
        }
        
        if router_public_ip:
            result["router_public_ip"] = router_public_ip
        
        # Load architecture
        architecture = load_architecture_from_config(config_path)
        if architecture:
            result["architecture"] = architecture
        
        # Load Guacamole info
        guacamole_info = load_guacamole_info_from_config(config_path)
        if guacamole_info:
            result["guacamole_info"] = guacamole_info
        
        operation_dict["result"] = result
        
        # Add wireguard config if status is wait_for_vpn
        if status == "wait_for_vpn":
            # First try to get wireguard_config from config YAML file (general.wireguard_config)
            wireguard_config = general.get("wireguard_config")
            if wireguard_config:
                operation_dict["wireguard_config"] = wireguard_config
                # Also set the path for reference
                wireguard_config_path = os.path.join(WIREGUARD_CONFIG_DIR, f"{attack_range_id}.conf")
                operation_dict["wireguard_config_path"] = wireguard_config_path
            else:
                # Fallback: read from file system (for backward compatibility)
                wireguard_config_path = os.path.join(WIREGUARD_CONFIG_DIR, f"{attack_range_id}.conf")
                if os.path.exists(wireguard_config_path):
                    operation_dict["wireguard_config_path"] = wireguard_config_path
                    try:
                        with open(wireguard_config_path, 'r') as f:
                            operation_dict["wireguard_config"] = f.read()
                    except Exception:
                        pass

        # Add sharing (general.sharing: name -> config) when available
        sharing = general.get("sharing")
        if sharing and isinstance(sharing, dict):
            operation_dict["sharing"] = sharing

        return operation_dict
    except Exception as e:
        import sys
        print(f"Warning: Failed to load operation from {config_path}: {e}", file=sys.stderr)
        return None


@app.get(
    "/attack-range/list",
    tags=[attack_range_tag],
    responses={200: AttackRangeListResponse},
    summary="List all running attack ranges",
    description="Get a list of all attack ranges with their current status"
)
def list_attack_ranges():
    """List all running attack ranges."""
    operations_list = []
    seen_attack_range_ids = set()
    
    # First, collect all operations from running_operations
    with operations_lock:
        for ar_id, op in running_operations.items():
            operation_dict = {**op, "attack_range_id": ar_id}
            seen_attack_range_ids.add(ar_id)
            
            # Get config path to check for status and other info
            config_path = op.get("config_path") or get_config_path_from_attack_range_id(ar_id)
            
            # Skip if status is "completed" (successfully destroyed attack ranges)
            if operation_dict.get("status") == "completed":
                continue
            
            # If config file exists, prioritize status from config file over running_operations
            if config_path and os.path.exists(config_path):
                config_content = load_yaml_file(config_path)
                if config_content:
                    general = config_content.get("general", {})
                    # Update status from config file if it exists (config file is source of truth)
                    config_status = general.get("status")
                    if config_status:
                        operation_dict["status"] = config_status
                        # Skip if status is "completed" or "failed" after checking config file
                        if config_status in ["completed", "failed"]:
                            continue
                    
                    # If template_name is missing, try to load it from config file
                    if not operation_dict.get("template_name"):
                        template_name = general.get("name")
                        if template_name:
                            operation_dict["template_name"] = template_name
                    
                    # Load attack_range_name from config file
                    attack_range_name = general.get("attack_range_name")
                    if attack_range_name:
                        operation_dict["attack_range_name"] = attack_range_name
            
            # If running and has config_file, load architecture and Guacamole info
            if operation_dict.get("status") == "running" and op.get("result") and op["result"].get("config_file"):
                config_path = op["result"]["config_file"]
                architecture = load_architecture_from_config(config_path)
                if architecture:
                    if "result" not in operation_dict:
                        operation_dict["result"] = {}
                    operation_dict["result"]["architecture"] = architecture
                
                # Load Guacamole info
                guacamole_info = load_guacamole_info_from_config(config_path)
                if guacamole_info:
                    if "result" not in operation_dict:
                        operation_dict["result"] = {}
                    operation_dict["result"]["guacamole_info"] = guacamole_info
            
            operations_list.append(OperationStatusResponse(**operation_dict))
    
    # Then, scan config directory for config files that aren't in running_operations
    if os.path.exists(CONFIG_DIR):
        yml_files = glob.glob(os.path.join(CONFIG_DIR, "*.yml"))
        for yml_file in yml_files:
            # Load operation from config file
            operation_dict = load_operation_from_config(yml_file)
            if not operation_dict:
                continue
            
            attack_range_id = operation_dict.get("attack_range_id")
            if not attack_range_id:
                continue
            
            # Skip if already in running_operations
            if attack_range_id in seen_attack_range_ids:
                continue
            
            # Skip if status is "completed" (successfully destroyed attack ranges)
            status = operation_dict.get("status")
            if status == "completed":
                continue
            
            seen_attack_range_ids.add(attack_range_id)
            operations_list.append(OperationStatusResponse(**operation_dict))
    
    return jsonify(AttackRangeListResponse(attack_ranges=operations_list).model_dump()), 200


@app.post(
    "/attack-range/simulate",
    tags=[attack_range_tag],
    responses={200: SimulateResponse, 400: ErrorResponse, 404: ErrorResponse, 500: ErrorResponse},
    summary="Run Atomic Red Team simulation",
    description="Run Atomic Red Team techniques and/or individual atomic tests (technique id + auto_generated_guid) against a target server in a running attack range. This is a synchronous operation."
)
def simulate_attack_range(body: SimulateRequest):
    """Run Atomic Red Team simulation on a target server."""
    try:
        # Find config file for this attack_range_id
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
        config_path = os.path.join(config_dir, f"{body.attack_range_id}.yml")
        
        if not os.path.exists(config_path):
            return jsonify(ErrorResponse(
                message=f"Attack range with ID '{body.attack_range_id}' not found",
                details=f"Config file not found: {config_path}"
            ).model_dump()), 404
        
        # Load config
        config = load_yaml_file(config_path)
        if not config:
            return jsonify(ErrorResponse(
                message=f"Failed to load config for attack range '{body.attack_range_id}'"
            ).model_dump()), 500
        
        # Validate attack range is running
        status = config.get("general", {}).get("status", "")
        if status not in ["running", "completed"]:
            return jsonify(ErrorResponse(
                message=f"Cannot run simulation. Attack range status is '{status}'. Must be 'running' or 'completed'."
            ).model_dump()), 400
        
        # Validate target exists
        attack_range_config = config.get("attack_range", [])
        target_found = False
        for server in attack_range_config:
            if server.get("name") == body.target:
                target_found = True
                break
        
        if not target_found:
            available_servers = [s.get("name") for s in attack_range_config if s.get("name")]
            return jsonify(ErrorResponse(
                message=f"Target server '{body.target}' not found in attack range configuration",
                details=f"Available servers: {', '.join(available_servers) if available_servers else 'None'}"
            ).model_dump()), 400
        
        # Create controller and run simulation
        controller = AttackRangeController(config, config_path=config_path)
        try:
            atomics_payload = [
                {"technique": a.technique, "guid": a.guid} for a in body.atomics
            ]
            atomic_files_payload = [
                a.model_dump(exclude_none=True) for a in body.atomic_files
            ]
            execution_output = controller.simulate(
                body.target,
                body.techniques,
                atomics_payload,
                atomic_files_payload,
            )
        except ValueError as e:
            # Validation errors (status, target not found, etc.)
            error_msg = str(e)
            print(f"[API] Simulation validation failed: {error_msg}", file=sys.stderr)
            return jsonify(ErrorResponse(
                message="Simulation validation failed",
                details=error_msg
            ).model_dump()), 400
        except RuntimeError as e:
            # Execution errors (role installation, playbook execution, etc.)
            error_msg = str(e)
            print(f"[API] Simulation execution failed: {error_msg}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return jsonify(ErrorResponse(
                message="Simulation execution failed",
                details=error_msg
            ).model_dump()), 500
        except SystemExit as e:
            # Some methods may still call sys.exit, catch it
            error_msg = f"Process exited with code {e.code if hasattr(e, 'code') else 'unknown'}"
            print(f"[API] Simulation failed with SystemExit: {error_msg}", file=sys.stderr)
            return jsonify(ErrorResponse(
                message="Simulation failed",
                details=error_msg
            ).model_dump()), 500
        
        parts = []
        if body.techniques:
            parts.append(f"{len(body.techniques)} technique(s)")
        if body.atomics:
            parts.append(f"{len(body.atomics)} atomic test(s)")
        if body.atomic_files:
            parts.append(f"{len(body.atomic_files)} atomic file(s)")
        summary = " and ".join(parts) if parts else "simulation"

        execution_status = None
        execution_summary = None
        if isinstance(execution_output, dict):
            execution_status = execution_output.get("status")
            summary_payload = execution_output.get("summary")
            if isinstance(summary_payload, dict):
                execution_summary = summary_payload

        return jsonify(SimulateResponse(
            status="success",
            message=f"Successfully executed {summary} on {body.target}",
            attack_range_id=body.attack_range_id,
            target=body.target,
            techniques=body.techniques,
            atomics=body.atomics,
            atomic_files=body.atomic_files,
            execution_status=execution_status,
            execution_summary=execution_summary,
            execution_output=execution_output
        ).model_dump()), 200
        
    except ValueError as e:
        # Validation errors from controller initialization or other validation
        return jsonify(ErrorResponse(
            message="Simulation validation failed",
            details=str(e)
        ).model_dump()), 400
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        return jsonify(ErrorResponse(
            message="Failed to run simulation",
            details=f"{str(e)}\n\n{error_traceback}"
        ).model_dump()), 500


@app.post(
    "/attack-range/splunk/export",
    tags=[attack_range_tag],
    responses={200: SplunkExportResponse, 400: ErrorResponse, 404: ErrorResponse, 500: ErrorResponse},
    summary="Export raw events from Splunk",
    description=(
        "Run a Splunk search against the attack range Splunk server and return the _raw field of each event. "
        "Requires VPN connectivity to the range (Splunk management API on 10.0.2.x:8089). "
        "This is a synchronous operation."
    ),
)
def splunk_export_attack_range(body: SplunkExportRequest):
    """Export raw events from the Splunk server in a running attack range."""
    try:
        config_path = os.path.join(CONFIG_DIR, f"{body.attack_range_id}.yml")
        if not os.path.exists(config_path):
            return jsonify(ErrorResponse(
                message=f"Attack range with ID '{body.attack_range_id}' not found",
                details=f"Config file not found: {config_path}",
            ).model_dump()), 404

        config = load_yaml_file(config_path)
        if not config:
            return jsonify(ErrorResponse(
                message=f"Failed to load config for attack range '{body.attack_range_id}'",
            ).model_dump()), 500

        status = config.get("general", {}).get("status", "")
        if status not in ["running", "completed"]:
            return jsonify(ErrorResponse(
                message=f"Cannot export from Splunk. Attack range status is '{status}'. Must be 'running' or 'completed'.",
            ).model_dump()), 400

        try:
            events, metadata = export_raw_events(
                config,
                search=body.search,
                earliest_time=body.earliest_time,
                latest_time=body.latest_time,
                max_results=body.max_results,
            )
        except ValueError as e:
            return jsonify(ErrorResponse(
                message="Splunk export validation failed",
                details=str(e),
            ).model_dump()), 400
        except SplunkExportError as e:
            print(f"[API] Splunk export failed: {e}", file=sys.stderr)
            return jsonify(ErrorResponse(
                message="Splunk export failed",
                details=str(e),
            ).model_dump()), 500

        query = metadata["search"]
        return jsonify(SplunkExportResponse(
            status="success",
            message=f"Exported {metadata['event_count']} event(s) from Splunk",
            attack_range_id=body.attack_range_id,
            search=query,
            earliest_time=metadata["earliest_time"],
            latest_time=metadata["latest_time"],
            splunk_host=metadata["splunk_host"],
            event_count=metadata["event_count"],
            events=events,
        ).model_dump()), 200

    except Exception as e:
        error_traceback = traceback.format_exc()
        return jsonify(ErrorResponse(
            message="Failed to export Splunk events",
            details=f"{str(e)}\n\n{error_traceback}",
        ).model_dump()), 500


@app.post(
    "/attack-range/share",
    tags=[attack_range_tag],
    responses={200: ShareResponse, 400: ErrorResponse, 404: ErrorResponse, 500: ErrorResponse},
    summary="Share attack range",
    description="Generate a new WireGuard client config for the given name, run the VPN playbooks with the updated vpn_clients, save to general.sharing, and return the config. Requires status wait_for_vpn or running."
)
def share_attack_range(body: ShareRequest):
    """Share an attack range by generating a new WireGuard config for the given name."""
    try:
        config_path = os.path.join(CONFIG_DIR, f"{body.attack_range_id}.yml")
        if not os.path.exists(config_path):
            return jsonify(ErrorResponse(
                message=f"Attack range with ID '{body.attack_range_id}' not found",
                details=f"Config file not found: {config_path}"
            ).model_dump()), 404

        config = load_yaml_file(config_path)
        if not config:
            return jsonify(ErrorResponse(
                message=f"Failed to load config for attack range '{body.attack_range_id}'"
            ).model_dump()), 500

        controller = AttackRangeController(config, config_path=config_path)
        config_content = controller.share(body.name)

        return jsonify(ShareResponse(
            name=body.name,
            config=config_content,
            message=f"Share '{body.name}' created. Config saved to general.sharing and printed below."
        ).model_dump()), 200

    except ValueError as e:
        return jsonify(ErrorResponse(
            message="Share validation failed",
            details=str(e)
        ).model_dump()), 400
    except RuntimeError as e:
        return jsonify(ErrorResponse(
            message="Share execution failed",
            details=str(e)
        ).model_dump()), 500
    except Exception as e:
        import traceback
        return jsonify(ErrorResponse(
            message="Failed to share attack range",
            details=traceback.format_exc()
        ).model_dump()), 500


@app.post(
    "/attack-range/update-name",
    tags=[attack_range_tag],
    responses={200: UpdateNameResponse, 400: ErrorResponse, 404: ErrorResponse, 500: ErrorResponse},
    summary="Update attack range name",
    description="Update the attack_range_name in the config file. Requires status running."
)
def update_attack_range_name(body: UpdateNameRequest):
    """Update the attack range name in the config file."""
    try:
        config_path = os.path.join(CONFIG_DIR, f"{body.attack_range_id}.yml")
        if not os.path.exists(config_path):
            return jsonify(ErrorResponse(
                message=f"Attack range with ID '{body.attack_range_id}' not found",
                details=f"Config file not found: {config_path}"
            ).model_dump()), 404

        config = load_yaml_file(config_path)
        if not config:
            return jsonify(ErrorResponse(
                message=f"Failed to load config for attack range '{body.attack_range_id}'"
            ).model_dump()), 500

        # Validate attack range is running
        status = config.get("general", {}).get("status", "")
        if status != "running":
            return jsonify(ErrorResponse(
                message=f"Cannot update name. Attack range status is '{status}'. Must be 'running'."
            ).model_dump()), 400

        # Update attack_range_name in config
        if "general" not in config:
            config["general"] = {}
        config["general"]["attack_range_name"] = body.attack_range_name

        # Save updated config
        save_yaml_file(config_path, config)

        return jsonify(UpdateNameResponse(
            status="success",
            message=f"Attack range name updated to '{body.attack_range_name}'",
            attack_range_id=body.attack_range_id,
            attack_range_name=body.attack_range_name
        ).model_dump()), 200

    except ValueError as e:
        return jsonify(ErrorResponse(
            message="Update name validation failed",
            details=str(e)
        ).model_dump()), 400
    except Exception as e:
        import traceback
        return jsonify(ErrorResponse(
            message="Failed to update attack range name",
            details=f"{str(e)}\n\n{traceback.format_exc()}"
        ).model_dump()), 500


# ============================================================================
# TEMPLATE ENDPOINTS
# ============================================================================

@app.get(
    "/templates",
    tags=[template_tag],
    responses={200: TemplateListResponse},
    summary="List templates",
    description="Get a list of all available attack range templates. Includes provider availability information."
)
def list_templates():
    """List all available templates."""
    templates = get_templates()
    
    # Get provider availability (check for test_missing parameter)
    test_missing = request.args.get('test_missing', None)
    provider_availability = get_provider_availability(test_missing=test_missing)
    
    # Create a map of provider -> availability
    availability_map = {p.provider: p.available for p in provider_availability}
    
    # Add availability info to templates (we'll extend TemplateInfo in the response)
    templates_with_availability = []
    for template in templates:
        template_dict = template.model_dump()
        template_dict['provider_available'] = availability_map.get(template.provider, False)
        templates_with_availability.append(template_dict)
    
    return jsonify({
        "templates": templates_with_availability,
        "provider_availability": {p.provider: p.model_dump() for p in provider_availability}
    })


@app.get(
    "/templates/<provider>/<name>",
    tags=[template_tag],
    responses={200: TemplateContentResponse, 404: ErrorResponse},
    summary="Get template content",
    description="Get the content of a specific template by provider and name"
)
def get_template(path: TemplatePath):
    """Get content of a specific template."""
    provider = path.provider
    name = path.name
    
    template_path = os.path.join(TEMPLATES_DIR, provider, name)
    if not template_path.endswith('.yml'):
        template_path += '.yml'
    
    if not os.path.exists(template_path):
        return jsonify(ErrorResponse(
            message=f"Template not found: {provider}/{name}"
        ).model_dump()), 404
    
    try:
        content = load_yaml_file(template_path)
        return jsonify(TemplateContentResponse(
            name=name if name.endswith('.yml') else f"{name}.yml",
            provider=provider,
            content=content
        ).model_dump())
    except Exception as e:
        return jsonify(ErrorResponse(
            message="Failed to load template",
            details=str(e)
        ).model_dump()), 500


@app.get(
    "/templates/cloud-fields/<provider>",
    tags=[template_tag],
    summary="Get cloud-specific fields schema",
    description="Get the schema of cloud-specific config fields for a provider (for build form: labels, types, dropdown options)."
)
def get_template_cloud_fields(path: CloudFieldsProviderPath):
    """Return cloud-specific fields schema for the given provider (aws, azure, gcp)."""
    provider = path.provider
    schema = get_cloud_fields_schema(provider)
    if not schema:
        return jsonify(ErrorResponse(
            message=f"Unknown provider: {provider}",
            details="Use aws, azure, or gcp"
        ).model_dump()), 404
    return jsonify({"provider": provider, "fields": schema})


@app.get(
    "/templates/cloud-fields/gcp/zones",
    tags=[template_tag],
    summary="Get GCP zones for region",
    description="Get list of zones for a GCP region (for zone dropdown when region changes)."
)
def get_gcp_zones():
    """Return zones for the given GCP region (query param: region)."""
    region = request.args.get("region", "")
    zones = get_gcp_zones_for_region(region)
    return jsonify({"region": region, "zones": zones})


def _is_ipv4(ip: str) -> bool:
    """Return True if the string is a valid IPv4 address."""
    if not ip or not ip.strip():
        return False
    parts = ip.strip().split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not p.isdigit() or not (0 <= int(p) <= 255):
            return False
    return True


def _fetch_public_ipv4() -> str:
    """Fetch the server's outbound public IPv4 via ipify (no CORS when called from backend). Returns empty string on failure."""
    try:
        from urllib.request import urlopen, Request
        from urllib.error import URLError, HTTPError
        req = Request("https://api.ipify.org?format=json", headers={"User-Agent": "AttackRange/1.0"})
        with urlopen(req, timeout=5) as resp:
            data = resp.read().decode("utf-8")
        import json
        out = json.loads(data)
        ip = (out.get("ip") or "").strip()
        return ip if _is_ipv4(ip) else ""
    except Exception:
        return ""


@app.get(
    "/public-ip",
    tags=[template_tag],
    summary="Get public IPv4 for whitelist suggestion",
    description="Returns the public IPv4 as seen from the server (e.g. for ip_whitelist). Fetched server-side to avoid CORS; same shape as /suggested-ip."
)
def get_public_ip():
    """Return public IPv4 from an external service (ipify), as CIDR x.x.x.x/32. No CORS issues since request is server-side."""
    ip = _fetch_public_ipv4()
    cidr = f"{ip}/32" if ip else ""
    return jsonify({"ip": ip, "cidr": cidr})


@app.get(
    "/suggested-ip",
    tags=[template_tag],
    summary="Get suggested client IP for whitelist",
    description="Returns the public IPv4 of the client as seen by the server, as CIDR (e.g. 1.2.3.4/32). Uses X-Forwarded-For when behind a proxy. Only IPv4 is returned."
)
def get_suggested_ip():
    """Return the client IPv4 as seen by the server, as CIDR for ip_whitelist (e.g. 1.2.3.4/32). Only IPv4 is returned."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First element is the original client when behind a proxy
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.remote_addr or ""
    if not _is_ipv4(client_ip):
        client_ip = ""
    cidr = f"{client_ip}/32" if client_ip else ""
    return jsonify({"ip": client_ip, "cidr": cidr})


# ============================================================================
# PROVIDER ENDPOINTS
# ============================================================================

@app.get(
    "/providers/check",
    tags=[provider_tag],
    responses={200: ProviderCheckResponse},
    summary="Check provider CLI availability",
    description="Check which cloud provider CLIs (aws, azure, gcp) are installed and available. Use ?test_missing=<provider> to simulate a missing provider for testing."
)
def check_providers():
    """Check availability of cloud provider CLIs."""
    # Get test_missing parameter from query string
    test_missing = request.args.get('test_missing', None)
    
    providers = get_provider_availability(test_missing=test_missing)
    return jsonify(ProviderCheckResponse(providers=providers).model_dump()), 200


# ============================================================================
# CONFIG ENDPOINTS
# ============================================================================

@app.get(
    "/configs",
    tags=[config_tag],
    responses={200: ConfigListResponse},
    summary="List saved configs",
    description="Get a list of all saved attack range configurations"
)
def list_configs():
    """List all saved configurations."""
    configs = []
    
    if not os.path.exists(CONFIG_DIR):
        return jsonify(ConfigListResponse(configs=configs).model_dump())
    
    yml_files = glob.glob(os.path.join(CONFIG_DIR, "*.yml"))
    for yml_file in yml_files:
        attack_range_id = os.path.splitext(os.path.basename(yml_file))[0]
        modified_time = datetime.fromtimestamp(os.path.getmtime(yml_file)).isoformat()
        
        configs.append(ConfigInfo(
            attack_range_id=attack_range_id,
            path=yml_file,
            modified_time=modified_time
        ))
    
    # Sort by modified time (newest first)
    configs.sort(key=lambda x: x.modified_time, reverse=True)
    
    return jsonify(ConfigListResponse(configs=configs).model_dump())


@app.get(
    "/configs/<config_id>",
    tags=[config_tag],
    responses={200: ConfigContentResponse, 404: ErrorResponse},
    summary="Get config content",
    description="Get the content of a saved configuration by ID"
)
def get_config(path: ConfigIdPath):
    """Get content of a specific configuration."""
    config_id = path.config_id
    
    config_filename = f"{config_id}.yml" if not config_id.endswith('.yml') else config_id
    config_path = os.path.join(CONFIG_DIR, config_filename)
    
    if not os.path.exists(config_path):
        return jsonify(ErrorResponse(
            message=f"Config not found: {config_id}"
        ).model_dump()), 404
    
    try:
        content = load_yaml_file(config_path)
        return jsonify(ConfigContentResponse(
            attack_range_id=config_id,
            content=content
        ).model_dump())
    except Exception as e:
        return jsonify(ErrorResponse(
            message="Failed to load config",
            details=str(e)
        ).model_dump()), 500


if __name__ == "__main__":
    # Ensure config and wireguard_config directories exist
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(WIREGUARD_CONFIG_DIR, exist_ok=True)
    
    # Run the Flask app
    app.run(host="0.0.0.0", port=4000, debug=False)
