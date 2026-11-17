# Attack Range Code Architecture

This document describes the refactored code architecture for the Attack Range controller.

## Overview

The Attack Range controller has been refactored from a single monolithic file (~2459 lines) into a modular, well-structured architecture following SOLID principles and Python best practices.

## Directory Structure

```
attack_range/
├── __init__.py
├── attack_range_controller.py          # Main orchestrator (slim, ~260 lines)
├── ARCHITECTURE.md                      # This file
├── managers/                            # Manager modules
│   ├── __init__.py
│   ├── config_manager.py               # Configuration management
│   ├── terraform_manager.py            # Terraform operations
│   ├── ansible_manager.py              # Ansible operations
│   ├── ssh_manager.py                  # SSH key management
│   └── backend_manager.py              # Remote backend management
└── cloud_providers/                     # Cloud provider implementations
    ├── __init__.py
    ├── base_provider.py                # Abstract base class
    ├── aws_provider.py                 # AWS-specific operations
    ├── azure_provider.py               # Azure-specific operations
    └── gcp_provider.py                 # GCP-specific operations
```

## Architecture Components

### 1. Main Controller (`attack_range_controller.py`)

**Responsibility**: Orchestration and workflow coordination

The main controller is now a slim orchestrator that:
- Initializes all managers and cloud providers
- Coordinates the build and destroy workflows
- Delegates specific tasks to appropriate managers
- Maintains no business logic itself

**Key Methods**:
- `build()`: Orchestrates the infrastructure build process
- `destroy()`: Orchestrates the infrastructure teardown process

### 2. Managers

Managers handle specific aspects of the attack range infrastructure:

#### ConfigManager (`managers/config_manager.py`)
**Responsibility**: Configuration validation and management

- Validates zeek configuration for cloud providers
- Generates and manages attack range IDs
- Handles config file operations (save, load, remove)
- Manages config folder and file discovery

#### TerraformManager (`managers/terraform_manager.py`)
**Responsibility**: Terraform operations

- Initializes Terraform
- Applies/destroys Terraform configurations
- Retrieves Terraform outputs
- Manages Terraform variables

#### AnsibleManager (`managers/ansible_manager.py`)
**Responsibility**: Ansible operations

- Updates inventory files
- Generates and updates playbooks
- Runs Ansible playbooks
- Installs Ansible Galaxy roles
- Waits for SSH availability
- Manages VPN connection prompts

#### SSHManager (`managers/ssh_manager.py`)
**Responsibility**: SSH key management

- Generates SSH key pairs
- Uploads keys to cloud providers (when needed)
- Cleans up SSH keys
- Updates configuration with key paths

#### BackendManager (`managers/backend_manager.py`)
**Responsibility**: Terraform remote backend management

- Sets up remote state storage (S3/Azure Storage/GCS)
- Creates necessary resources (buckets, tables, containers)
- Cleans up remote backend resources
- Updates backend configuration files

### 3. Cloud Providers

Cloud provider classes implement cloud-specific operations:

#### BaseCloudProvider (`cloud_providers/base_provider.py`)
**Responsibility**: Define cloud provider interface

Abstract base class defining the contract for all cloud providers:
- `get_region()`: Get cloud provider region/location
- `sanitize_name()`: Sanitize resource names
- `check_backend_exists()`: Check if backend storage exists
- `create_backend()`: Create backend storage
- `delete_backend()`: Delete backend storage
- `import_ssh_key()`: Import SSH key (if applicable)
- `delete_ssh_key()`: Delete SSH key (if applicable)
- `write_backend_config()`: Create/update backend configuration file
- `get_backend_params()`: Get backend parameters for the current provider

#### AWSProvider (`cloud_providers/aws_provider.py`)
**Responsibility**: AWS-specific operations

- Manages S3 buckets for state storage (with S3 native locking via use_lockfile)
- Imports/deletes EC2 key pairs
- Sanitizes names for S3 requirements

#### AzureProvider (`cloud_providers/azure_provider.py`)
**Responsibility**: Azure-specific operations

- Manages Storage Accounts and Containers
- Creates/deletes resource groups
- Handles Azure-specific naming constraints
- Note: SSH keys are used directly in VM config

#### GCPProvider (`cloud_providers/gcp_provider.py`)
**Responsibility**: GCP-specific operations

- Manages GCS buckets for state storage
- Handles GCP project and region configuration
- Sanitizes names for GCS requirements
- Note: SSH keys are used directly in VM config

## Design Principles

### 1. Separation of Concerns
Each component has a single, well-defined responsibility:
- Controllers orchestrate workflows
- Managers handle specific domains (config, terraform, ansible, etc.)
- Providers abstract cloud-specific operations

### 2. Single Responsibility Principle (SRP)
Each class has one reason to change:
- `ConfigManager` changes only when config logic changes
- `AWSProvider` changes only when AWS operations change
- etc.

### 3. Open/Closed Principle (OCP)
The system is open for extension but closed for modification:
- New cloud providers can be added by extending `BaseCloudProvider`
- No need to modify existing code

### 4. Dependency Inversion Principle (DIP)
High-level modules depend on abstractions:
- `AttackRangeController` depends on manager interfaces
- Managers depend on cloud provider abstractions
- Concrete implementations are injected

### 5. Interface Segregation Principle (ISP)
Interfaces are client-specific:
- `BaseCloudProvider` defines only methods all providers need
- Providers can add cloud-specific methods as needed

## Benefits of the New Architecture

### 1. Maintainability
- **Smaller files**: Each file is focused and easier to understand
- **Clear boundaries**: Changes are localized to specific modules
- **Reduced coupling**: Components interact through well-defined interfaces

### 2. Testability
- **Unit testing**: Each manager/provider can be tested independently
- **Mocking**: Interfaces make it easy to mock dependencies
- **Isolation**: Test failures are easier to diagnose

### 3. Extensibility
- **New cloud providers**: Add support by implementing `BaseCloudProvider`
- **New features**: Add managers without modifying existing code
- **Custom workflows**: Compose managers in different ways

### 4. Readability
- **Clear naming**: Class and method names describe their purpose
- **Logical organization**: Related functionality is grouped together
- **Documentation**: Each module has clear docstrings

### 5. Reusability
- **Composable**: Managers can be reused in different contexts
- **Modular**: Import only what you need
- **Flexible**: Easy to create specialized workflows

## Migration Notes

### Original File Backup
The original `attack_range_controller.py` has been backed up to:
```
attack_range/attack_range_controller.py.bak
```

### API Compatibility
The public API of `AttackRangeController` remains unchanged:
- `__init__(config, config_path)`
- `build()`
- `destroy()`

Existing code using the controller should work without modifications.

### Internal Changes
All internal methods (prefixed with `_`) have been moved to appropriate managers.
If you have code directly calling these methods, update it to use the managers.

## Usage Example

```python
from attack_range.attack_range_controller import AttackRangeController

# Initialize controller with config
config = {...}  # Your configuration dictionary
controller = AttackRangeController(config, config_path="path/to/config.yml")

# Build infrastructure
controller.build()

# Destroy infrastructure
controller.destroy()
```

## Testing Recommendations

### Unit Tests
Test each manager and provider independently:
```python
# Example: Test ConfigManager
from attack_range.managers.config_manager import ConfigManager

def test_generate_attack_range_id():
    config = {"general": {}}
    manager = ConfigManager(config, None, "/tmp", mock_logger)
    attack_range_id = manager.generate_and_set_attack_range_id()
    assert config["general"]["attack_range_id"] == attack_range_id
```

### Integration Tests
Test manager interactions:
```python
# Example: Test backend setup workflow
def test_backend_setup():
    # Mock cloud provider
    mock_provider = Mock(spec=BaseCloudProvider)
    backend_manager = BackendManager(terraform_dir, config, config_path, mock_provider, logger)
    
    # Test backend setup
    backend_manager.setup_remote_backend()
    
    # Verify cloud provider methods were called
    mock_provider.check_backend_exists.assert_called_once()
```

### End-to-End Tests
Test complete workflows in test environments.

## Future Enhancements

### Potential Improvements
1. **Async Operations**: Use async/await for parallel operations
2. **Event System**: Add event hooks for custom actions
3. **Plugin System**: Allow third-party extensions
4. **State Management**: Add state tracking and rollback capabilities
5. **Monitoring**: Add built-in metrics and monitoring
6. **Configuration Validation**: JSON Schema validation for configs

### Adding New Cloud Providers
1. Create new provider class extending `BaseCloudProvider`
2. Implement all abstract methods
3. Add cloud-specific methods as needed
4. Register in `_init_cloud_provider()` method
5. Update documentation

## Troubleshooting

### Import Errors
If you see import errors, ensure:
- All `__init__.py` files are present
- Python path includes the project root
- Dependencies are installed

### Manager Initialization
If managers fail to initialize:
- Check config dictionary structure
- Verify directory paths exist
- Ensure cloud provider credentials are configured

### Cloud Provider Issues
If cloud operations fail:
- Verify credentials and permissions
- Check region/location configuration
- Review cloud provider error messages

## Contributing

When contributing to this codebase:
1. Follow the existing architecture patterns
2. Add new functionality to appropriate managers
3. Create new managers for new domains
4. Keep the controller thin and orchestrative
5. Add tests for new components
6. Update this documentation

## Questions?

For questions or issues with the architecture:
- Review this document
- Check inline code documentation
- Look at existing implementations as examples
- Consult the backup file for original implementation
