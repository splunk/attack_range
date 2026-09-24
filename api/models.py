"""Pydantic models for API request and response validation."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, model_validator


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="API health status")
    version: str = Field(..., description="API version")


class BuildRequest(BaseModel):
    """Request model for building an attack range."""
    template: Optional[str] = Field(None, description="Template name or path (e.g., 'aws/splunk_minimal_aws', 'splunk_minimal_aws.yml') - Required for new builds")
    attack_range_id: Optional[str] = Field(None, description="Attack range ID to continue building (for phase 2 after VPN connection, or to retry the lab playbook after a lab-phase error)")
    cloud_overrides: Optional[Dict[str, Dict[str, Any]]] = Field(
        None,
        description="Cloud-specific values to inject into config when copying template to configs (e.g. {\"azure\": {\"location\": \"West Europe\", \"subscription_id\": \"xxx\"}})"
    )
    general_overrides: Optional[Dict[str, Any]] = Field(
        None,
        description="General config values to inject (e.g. {\"ip_whitelist\": \"1.2.3.4/32\", \"attack_range_password\": \"...\"})"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "template": "aws/splunk_minimal_aws"
                },
                {
                    "template": "azure/splunk_es_azure",
                    "cloud_overrides": {"azure": {"location": "West Europe", "subscription_id": "your-subscription-id"}}
                },
                {
                    "attack_range_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            ]
        }


class BuildResponse(BaseModel):
    """Response model for build operation."""
    status: str = Field(..., description="Build operation status")
    message: str = Field(..., description="Status message")
    attack_range_id: str = Field(..., description="Attack range ID (use this to continue build after VPN connection and check status)")
    phase: str = Field(..., description="Build phase (vpn or lab)")


class DestroyRequest(BaseModel):
    """Request model for destroying an attack range."""
    attack_range_id: str = Field(..., description="Attack range ID to destroy")

    class Config:
        json_schema_extra = {
            "example": {
                "attack_range_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class DestroyResponse(BaseModel):
    """Response model for destroy operation."""
    status: str = Field(..., description="Destroy operation status")
    message: str = Field(..., description="Status message")


class OperationStatusResponse(BaseModel):
    """Response model for operation status."""
    type: str = Field(..., description="Operation type (build or destroy)")
    status: str = Field(..., description="Operation status (queued, build_vpn, wait_for_vpn, build_lab, running, completed, failed, error)")
    created_time: str = Field(..., description="Time when operation was created")
    start_time: Optional[str] = Field(None, description="Time when operation started")
    end_time: Optional[str] = Field(None, description="Time when operation ended")
    attack_range_id: Optional[str] = Field(None, description="Attack range ID")
    attack_range_name: Optional[str] = Field(None, description="Attack range name (from general.attack_range_name)")
    template_name: Optional[str] = Field(None, description="Template name used for this attack range")
    router_public_ip: Optional[str] = Field(None, description="Router public IP address")
    wireguard_config: Optional[str] = Field(None, description="WireGuard VPN configuration (available during wait_for_vpn and lab-phase error retry)")
    wireguard_config_path: Optional[str] = Field(None, description="Path to WireGuard config file")
    sharing: Optional[Dict[str, str]] = Field(None, description="Shared WireGuard configs: name -> config (from general.sharing)")
    result: Optional[Dict[str, Any]] = Field(None, description="Operation result (for completed operations)")
    error: Optional[str] = Field(None, description="Error message (for failed operations)")
    error_phase: Optional[str] = Field(None, description="Build phase where error occurred")
    traceback: Optional[str] = Field(None, description="Error traceback (for failed operations)")
    terraform_running: Optional[bool] = Field(None, description="True while Terraform init/apply is in progress")
    abort_allowed: Optional[bool] = Field(None, description="True when abort is permitted for the current build state")


class ServerInfo(BaseModel):
    """Server information from template architecture."""
    name: str = Field(..., description="Server name")
    instance_type: Optional[str] = Field(None, description="Cloud instance type")
    ip_last_octet: Optional[int] = Field(None, description="Last octet of IP address")
    os_type: Optional[str] = Field(None, description="Operating system type (linux/windows)")
    roles: Optional[List[str]] = Field(None, description="List of Ansible roles")
    zeek: Optional[bool] = Field(None, description="Whether Zeek is installed")
    zeek_monitor: Optional[bool] = Field(None, description="Whether server is monitored by Zeek")


class TemplateInfo(BaseModel):
    """Template information."""
    name: str = Field(..., description="Template filename")
    provider: str = Field(..., description="Cloud provider (aws, azure, gcp)")
    path: str = Field(..., description="Full path to template file")
    description: Optional[str] = Field(None, description="Template description from general section")
    architecture: Optional[List[ServerInfo]] = Field(None, description="List of servers in the template architecture")


class TemplateListResponse(BaseModel):
    """Response model for template list."""
    templates: List[TemplateInfo] = Field(..., description="List of available templates")


class TemplateContentResponse(BaseModel):
    """Response model for template content."""
    name: str = Field(..., description="Template filename")
    provider: str = Field(..., description="Cloud provider")
    content: Dict[str, Any] = Field(..., description="Template configuration content")


class ConfigInfo(BaseModel):
    """Saved configuration information."""
    attack_range_id: str = Field(..., description="Attack range ID (filename without extension)")
    path: str = Field(..., description="Full path to config file")
    modified_time: Optional[str] = Field(None, description="Last modified timestamp")


class ConfigListResponse(BaseModel):
    """Response model for config list."""
    configs: List[ConfigInfo] = Field(..., description="List of saved configurations")


class ConfigContentResponse(BaseModel):
    """Response model for config content."""
    attack_range_id: str = Field(..., description="Attack range ID")
    content: Dict[str, Any] = Field(..., description="Configuration content")


class ErrorResponse(BaseModel):
    """Error response model."""
    status: str = Field("error", description="Status indicator")
    message: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details")


# Path parameter models
class AttackRangeIdPath(BaseModel):
    """Path parameter for attack range ID."""
    attack_range_id: str = Field(..., description="Attack range ID")


class TemplatePath(BaseModel):
    """Path parameters for template."""
    provider: str = Field(..., description="Cloud provider (aws, azure, gcp)")
    name: str = Field(..., description="Template name")


class CloudFieldsProviderPath(BaseModel):
    """Path parameter for cloud-fields endpoint (provider only)."""
    provider: str = Field(..., description="Cloud provider (aws, azure, gcp)")


class ConfigIdPath(BaseModel):
    """Path parameter for config ID."""
    config_id: str = Field(..., description="Configuration ID")


class AttackRangeListResponse(BaseModel):
    """Response model for attack range list."""
    attack_ranges: List[OperationStatusResponse] = Field(..., description="List of attack ranges with their status")


class ProviderAvailability(BaseModel):
    """Provider CLI availability information."""
    provider: str = Field(..., description="Cloud provider name (aws, azure, gcp)")
    available: bool = Field(..., description="Whether the CLI is installed and available")
    cli_command: str = Field(..., description="CLI command name (aws, az, gcloud)")
    error_message: Optional[str] = Field(None, description="Error message if CLI is not available")


class ProviderCheckResponse(BaseModel):
    """Response model for provider CLI check."""
    providers: List[ProviderAvailability] = Field(..., description="List of provider availability status")


class AtomicTestTarget(BaseModel):
    """A single Atomic Red Team test identified by technique and auto_generated_guid."""
    technique: str = Field(..., description="MITRE ATT&CK technique ID (e.g., T1003.001)")
    guid: str = Field(..., description="Atomic test auto_generated_guid from the ART YAML")


class AtomicSrcFileTarget(BaseModel):
    """Inline companion file deployed under atomics/<technique>/src/ on the target."""
    name: str = Field(..., description="Filename relative to the technique src/ directory")
    content_base64: str = Field(..., description="Base64-encoded file contents")


class AtomicFileTarget(BaseModel):
    """Custom atomic YAML to deploy on the target host before execution."""
    path: Optional[str] = Field(
        None,
        description="Absolute or playbook-relative path to atomic YAML on the Ansible controller",
    )
    content: Optional[str] = Field(
        None,
        description="Inline atomic YAML content (alternative to path)",
    )
    technique: Optional[str] = Field(
        None,
        description="MITRE technique ID override (defaults to attack_technique in YAML)",
    )
    guid: Optional[str] = Field(
        None,
        description="auto_generated_guid to run (defaults to sole test guid when file has one test)",
    )
    src_dir: Optional[str] = Field(
        None,
        description="Optional companion src/ directory path on the Ansible controller",
    )
    src_files: List["AtomicSrcFileTarget"] = Field(
        default_factory=list,
        description="Inline src/ files transferred with the atomic YAML",
    )

    @model_validator(mode="after")
    def require_path_or_content(self):
        if not self.path and not self.content:
            raise ValueError("Each atomic file entry must include either path or content.")
        return self


class SimulateRequest(BaseModel):
    """Request model for running Atomic Red Team simulation."""
    attack_range_id: str = Field(..., description="Attack range ID")
    target: str = Field(..., description="Target server name (must match a server name in attack_range config)")
    techniques: List[str] = Field(
        default_factory=list,
        description="MITRE ATT&CK technique IDs; runs all atomics for each technique (e.g., ['T1003.001'])",
    )
    atomics: List[AtomicTestTarget] = Field(
        default_factory=list,
        description="Specific atomics to run; each entry requires technique id and atomic test guid",
    )
    atomic_files: List[AtomicFileTarget] = Field(
        default_factory=list,
        description="Custom atomic YAML files to deploy and execute on the target host",
    )

    @model_validator(mode="after")
    def require_simulation_targets(self):
        if not self.techniques and not self.atomics and not self.atomic_files:
            raise ValueError(
                "Provide at least one technique ID, atomic (technique + guid), or atomic file."
            )
        return self

    class Config:
        json_schema_extra = {
            "example": {
                "attack_range_id": "550e8400-e29b-41d4-a716-446655440000",
                "target": "windows_server",
                "techniques": ["T1059.003"],
                "atomics": [
                    {
                        "technique": "T1003.001",
                        "guid": "0be2230c-9ab3-4ac2-8826-3199b9a0ebf8",
                    }
                ],
                "atomic_files": [
                    {"path": "/path/on/controller/custom.yaml"},
                ],
            }
        }


class AtomicExecutionSummary(BaseModel):
    """Aggregate counts for atomic simulation runs."""
    total: int = 0
    succeeded: int = 0
    failed: int = 0


class SimulateResponse(BaseModel):
    """Response model for simulation operation."""
    status: str = Field(..., description="Simulation status")
    message: str = Field(..., description="Status message")
    attack_range_id: str = Field(..., description="Attack range ID")
    target: str = Field(..., description="Target server name")
    techniques: List[str] = Field(default_factory=list, description="Technique IDs that were executed (all atomics per technique)")
    atomics: List[AtomicTestTarget] = Field(
        default_factory=list,
        description="Specific atomics that were executed (technique + guid pairs)",
    )
    atomic_files: List[AtomicFileTarget] = Field(
        default_factory=list,
        description="Custom atomic YAML files that were deployed and executed",
    )
    execution_status: Optional[str] = Field(
        None,
        description="Overall atomic execution status (success/failed/unknown) from Ansible",
    )
    execution_summary: Optional[AtomicExecutionSummary] = Field(
        None,
        description="Per-atomic success/failure counts",
    )
    execution_output: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured atomic execution results (results, summary, by_host)",
    )


class LocalRoleTarget(BaseModel):
    """Local Ansible role packaged as a base64-encoded gzip tarball."""
    content_base64: str = Field(
        ...,
        description="Base64-encoded gzip tarball of the role root (tasks/, meta/, etc.)",
    )
    name: Optional[str] = Field(
        None,
        description="Optional Ansible role name override (defaults to meta/main.yml or directory name)",
    )
    vars: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional variables passed to the role",
    )


class ApplyRoleRequest(BaseModel):
    """Request model for applying local Ansible roles after build."""
    attack_range_id: str = Field(..., description="Attack range ID")
    target: str = Field(..., description="Target server name (must match a server name in attack_range config)")
    roles: List[LocalRoleTarget] = Field(
        ...,
        min_length=1,
        description="Local roles to stage and execute on the target host",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "attack_range_id": "550e8400-e29b-41d4-a716-446655440000",
                "target": "splunk",
                "roles": [
                    {
                        "content_base64": "<base64-encoded-role-tarball>",
                        "vars": {"example_var": "value"},
                    }
                ],
            }
        }


class ApplyRoleResponse(BaseModel):
    """Response model for apply-role operation."""
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    attack_range_id: str = Field(..., description="Attack range ID")
    target: str = Field(..., description="Target server name")
    roles_applied: List[str] = Field(..., description="Resolved Ansible role names that were applied")
    execution_output: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional Ansible execution details",
    )


class SplunkExportRequest(BaseModel):
    """Request model for exporting raw events from the attack range Splunk server."""
    attack_range_id: str = Field(..., description="Attack range ID")
    search: str = Field(..., description="SPL search (with or without leading 'search')")
    earliest_time: str = Field(default="-24h", description="Splunk earliest_time bound (e.g. '-24h', '-1d@d')")
    latest_time: str = Field(default="now", description="Splunk latest_time bound (e.g. 'now')")
    max_results: int = Field(
        default=10000,
        ge=1,
        le=50000,
        description="Maximum number of events to export (Splunk export count)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "attack_range_id": "550e8400-e29b-41d4-a716-446655440000",
                "search": "index=* sourcetype=WinEventLog:Security",
                "earliest_time": "-1h",
                "latest_time": "now",
                "max_results": 1000,
            }
        }


class SplunkExportResponse(BaseModel):
    """Response model for Splunk raw event export."""
    status: str = Field(..., description="Export status")
    message: str = Field(..., description="Status message")
    attack_range_id: str = Field(..., description="Attack range ID")
    search: str = Field(..., description="Normalized SPL search that was executed")
    earliest_time: str = Field(..., description="Earliest time bound used")
    latest_time: str = Field(..., description="Latest time bound used")
    splunk_host: str = Field(..., description="Splunk management API host")
    event_count: int = Field(..., description="Number of events returned")
    events: List[str] = Field(
        ...,
        description="Splunk _raw field per event (one log line per event; join with newlines for line-delimited export)",
    )


class ShareRequest(BaseModel):
    """Request model for sharing an attack range (generate new WireGuard config)."""
    attack_range_id: str = Field(..., description="Attack range ID")
    name: str = Field(..., description="Share name (e.g. 'alice') — used as the new WireGuard client name")

    class Config:
        json_schema_extra = {
            "example": {
                "attack_range_id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "alice"
            }
        }


class ShareResponse(BaseModel):
    """Response model for share operation."""
    name: str = Field(..., description="Share name")
    config: str = Field(..., description="WireGuard configuration for the shared client")
    message: str = Field(..., description="Status message")


class UpdateNameRequest(BaseModel):
    """Request model for updating attack range name."""
    attack_range_id: str = Field(..., description="Attack range ID")
    attack_range_name: str = Field(..., description="New attack range name")

    class Config:
        json_schema_extra = {
            "example": {
                "attack_range_id": "550e8400-e29b-41d4-a716-446655440000",
                "attack_range_name": "My Attack Range"
            }
        }


class UpdateNameResponse(BaseModel):
    """Response model for update name operation."""
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    attack_range_id: str = Field(..., description="Attack range ID")
    attack_range_name: str = Field(..., description="Updated attack range name")
