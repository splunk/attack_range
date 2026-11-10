# Attack Range API

A REST API for building and managing Attack Range infrastructure with automated OpenAPI documentation powered by flask-openapi3.

## Features

- 🚀 **Two-Phase Build Process**: Build attack ranges with VPN setup first, then lab deployment after VPN connection
- 🔐 **Automatic VPN Setup**: WireGuard VPN server configured automatically with client config provided via API
- 📚 **Automatic OpenAPI Documentation**: Interactive API documentation automatically generated at `/openapi`
- 📋 **Template Management**: List and retrieve attack range templates
- 💾 **Configuration Management**: Save, list, and retrieve attack range configurations
- 🔄 **Asynchronous Operations**: Build and destroy operations run asynchronously with status tracking
- ✅ **Request Validation**: Automatic request/response validation with Pydantic models

## Installation

### Prerequisites

- Python 3.8 or higher
- All Attack Range dependencies (see main `requirements.txt`)

### Install Dependencies

All dependencies (including API dependencies) are now in the main requirements file:

```bash
# From project root
pip install -r requirements.txt
```

Or from the API directory:

```bash
cd api
pip install -r ../requirements.txt
```

## Running the API

### Development Mode

```bash
cd api
python app.py
```

The API will be available at `http://localhost:4000`

### Production Mode

For production deployment, use a production WSGI server like Gunicorn:

```bash
cd api
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:4000 app:app
```

## API Documentation

Once the API is running, you can access the interactive OpenAPI documentation at:

- **OpenAPI JSON**: `http://localhost:4000/openapi/openapi.json`
- **Swagger UI**: `http://localhost:4000/openapi/swagger`
- **Redoc**: `http://localhost:4000/openapi/redoc`

## API Endpoints

### Health Check

#### `GET /health`

Check if the API is running and healthy.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Attack Range Operations

#### `POST /attack-range/build`

Build a new attack range infrastructure OR continue an existing build after VPN connection. This is an asynchronous two-phase operation.

**Two-Phase Build Process:**
1. **Phase 1 (VPN Setup)**: Start with `template` - builds VPN infrastructure and generates WireGuard config
2. **Wait for VPN**: User activates VPN using the config from operation status
3. **Phase 2 (Lab Setup)**: Continue with `attack_range_id` - builds the actual lab infrastructure

**Request Body (Phase 1 - Start new build):**
```json
{
  "template": "aws/splunk_minimal_aws"
}
```

**Request Body (Phase 2 - Continue after VPN):**
```json
{
  "attack_range_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Template formats supported:**
- `aws/splunk_minimal_aws` - provider/template_name
- `splunk_minimal_aws` - searches in all provider directories
- `splunk_minimal_aws.yml` - with extension

**Response (202 Accepted):**
```json
{
  "status": "accepted",
  "message": "Build operation started (VPN phase). Attack Range ID: ...",
  "attack_range_id": "550e8400-e29b-41d4-a716-446655440000",
  "phase": "vpn"
}
```

#### `POST /attack-range/destroy`

Destroy an existing attack range infrastructure.

**Request Body:**
```json
{
  "attack_range_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (202 Accepted):**
```json
{
  "status": "accepted",
  "message": "Destroy operation started. Attack Range ID: 550e8400-e29b-41d4-a716-446655440000"
}
```

#### `GET /attack-range/status/{attack_range_id}`

Get the status of a build or destroy operation by attack_range_id.

**Response (during VPN setup):**
```json
{
  "type": "build",
  "status": "build_vpn",
  "created_time": "2026-01-13T10:30:00",
  "start_time": "2026-01-13T10:30:01",
  "attack_range_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (waiting for VPN connection):**
```json
{
  "type": "build",
  "status": "wait_for_vpn",
  "created_time": "2026-01-13T10:30:00",
  "start_time": "2026-01-13T10:30:01",
  "attack_range_id": "550e8400-e29b-41d4-a716-446655440000",
  "router_public_ip": "1.2.3.4",
  "wireguard_config": "[Interface]\nPrivateKey = ...\n[Peer]\n...",
  "wireguard_config_path": "/path/to/wireguard_config/550e8400-e29b-41d4-a716-446655440000.conf"
}
```

**Note:** WireGuard configs are automatically saved to the `wireguard_config/` folder with the filename `{attack_range_id}.conf`.

**Status values:**
- `queued`: Operation is queued but not started
- `build_vpn`: Building VPN infrastructure (Phase 1)
- `wait_for_vpn`: Waiting for user to connect VPN (includes `wireguard_config`)
- `build_lab`: Building lab infrastructure (Phase 2)
- `running`: Attack range is fully deployed and running
- `error`: Operation failed (includes `error`, `error_phase`, and `traceback` fields)

#### `POST /attack-range/apply-role`

Stage and execute local Ansible roles against a target server in a running attack range. This is a **synchronous** operation. The attack range must be in `running` or `completed` status.

Each role is provided as a **base64-encoded gzip tarball** of the role root directory (`tasks/`, `meta/`, etc.). Package a role with:

```bash
tar czf my_role.tar.gz -C /path/to/parent my_role
ROLE_B64=$(base64 -i my_role.tar.gz | tr -d '\n')
```

**Request Body:**
```json
{
  "attack_range_id": "550e8400-e29b-41d4-a716-446655440000",
  "target": "splunk",
  "roles": [
    {
      "content_base64": "<base64-encoded-role-tarball>",
      "name": "optional.namespace.role_name",
      "vars": {
        "example_var": "value"
      }
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Successfully applied 1 role(s) on splunk",
  "attack_range_id": "550e8400-e29b-41d4-a716-446655440000",
  "target": "splunk",
  "roles_applied": ["custom.my_role"],
  "execution_output": null
}
```

### Template Management

#### `GET /templates`

List all available attack range templates.

**Response:**
```json
{
  "templates": [
    {
      "name": "splunk_minimal_aws.yml",
      "provider": "aws",
      "path": "/path/to/templates/aws/splunk_minimal_aws.yml"
    },
    {
      "name": "splunk_full_azure.yml",
      "provider": "azure",
      "path": "/path/to/templates/azure/splunk_full_azure.yml"
    }
  ]
}
```

#### `GET /templates/{provider}/{name}`

Get the content of a specific template.

**Example:** `GET /templates/aws/splunk_minimal_aws`

**Response:**
```json
{
  "name": "splunk_minimal_aws.yml",
  "provider": "aws",
  "content": {
    "general": {
      "attack_range_password": "changeme123!",
      ...
    },
    ...
  }
}
```

### Configuration Management

#### `GET /configs`

List all saved attack range configurations.

**Response:**
```json
{
  "configs": [
    {
      "attack_range_id": "550e8400-e29b-41d4-a716-446655440000",
      "path": "/path/to/config/550e8400-e29b-41d4-a716-446655440000.yml",
      "modified_time": "2026-01-13T10:30:00"
    }
  ]
}
```

#### `GET /configs/{config_id}`

Get the content of a saved configuration.

**Example:** `GET /configs/550e8400-e29b-41d4-a716-446655440000`

**Response:**
```json
{
  "attack_range_id": "550e8400-e29b-41d4-a716-446655440000",
  "content": {
    "general": {
      "attack_range_id": "550e8400-e29b-41d4-a716-446655440000",
      ...
    },
    ...
  }
}
```

## Usage Examples

### Using cURL

#### Build an attack range (two-phase process):

```bash
# Phase 1: Start build with template
RESPONSE=$(curl -X POST http://localhost:4000/attack-range/build \
  -H "Content-Type: application/json" \
  -d '{
    "template": "aws/splunk_minimal_aws"
  }')

# Extract attack_range_id from response
ATTACK_RANGE_ID=$(echo $RESPONSE | jq -r '.attack_range_id')

echo "Attack Range ID: $ATTACK_RANGE_ID"

# Check status until wait_for_vpn
while true; do
  STATUS=$(curl -s http://localhost:4000/attack-range/status/$ATTACK_RANGE_ID | jq -r '.status')
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "wait_for_vpn" ]; then
    # Get WireGuard config (also automatically saved to wireguard_config/ folder)
    curl -s http://localhost:4000/attack-range/status/$ATTACK_RANGE_ID | \
      jq -r '.wireguard_config' > attack_range.conf
    
    echo "WireGuard config saved to attack_range.conf"
    echo "Note: Config also available at wireguard_config/$ATTACK_RANGE_ID.conf"
    echo "Please activate the VPN connection, then press Enter to continue..."
    read
    break
  fi
  
  sleep 10
done

# Phase 2: Continue build after VPN connection
curl -X POST http://localhost:4000/attack-range/build \
  -H "Content-Type: application/json" \
  -d "{
    \"attack_range_id\": \"$ATTACK_RANGE_ID\"
  }"

# Monitor final build
while true; do
  STATUS=$(curl -s http://localhost:4000/attack-range/status/$ATTACK_RANGE_ID | jq -r '.status')
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "running" ] || [ "$STATUS" = "error" ]; then
    break
  fi
  
  sleep 10
done
```

#### Destroy an attack range:

```bash
# List saved configs
curl http://localhost:4000/configs

# Destroy by attack_range_id
curl -X POST http://localhost:4000/attack-range/destroy \
  -H "Content-Type: application/json" \
  -d '{"attack_range_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

### Using Python

```python
import requests
import time

# API base URL
BASE_URL = "http://localhost:4000"

# Health check
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# List templates
response = requests.get(f"{BASE_URL}/templates")
templates = response.json()["templates"]
print(f"Found {len(templates)} templates")

# Phase 1: Start build with template
build_payload = {"template": "aws/basic_splunk"}
response = requests.post(f"{BASE_URL}/attack-range/build", json=build_payload)
result = response.json()
attack_range_id = result["attack_range_id"]
print(f"Build started - Attack Range ID: {attack_range_id}")

# Poll until VPN is ready
print("\nPhase 1: Building VPN infrastructure...")
while True:
    response = requests.get(f"{BASE_URL}/attack-range/status/{attack_range_id}")
    status_data = response.json()
    status = status_data['status']
    print(f"Status: {status}")
    
    if status == 'wait_for_vpn':
        # Save WireGuard config
        wireguard_config = status_data['wireguard_config']
        with open('attack_range.conf', 'w') as f:
            f.write(wireguard_config)
        print("\nWireGuard config saved to attack_range.conf")
        print("Please activate the VPN connection and press Enter to continue...")
        input()
        break
    elif status == 'error':
        print(f"Error: {status_data.get('error')}")
        exit(1)
    
    time.sleep(10)

# Phase 2: Continue build after VPN
print("\nPhase 2: Building lab infrastructure...")
continue_payload = {"attack_range_id": attack_range_id}
response = requests.post(f"{BASE_URL}/attack-range/build", json=continue_payload)
print(response.json())

# Poll until complete
while True:
    response = requests.get(f"{BASE_URL}/attack-range/status/{attack_range_id}")
    status_data = response.json()
    status = status_data['status']
    print(f"Status: {status}")
    
    if status == 'running':
        print("\n✓ Attack range is fully deployed!")
        print(f"Attack Range ID: {attack_range_id}")
        print(f"Router IP: {status_data.get('router_public_ip')}")
        break
    elif status == 'error':
        print(f"Error: {status_data.get('error')}")
        break
    
    time.sleep(10)
```

## Error Handling

All error responses follow a standard format:

```json
{
  "status": "error",
  "message": "Brief error description",
  "details": "Detailed error information (optional)"
}
```

Common HTTP status codes:
- `200`: Success
- `202`: Accepted (async operation started)
- `400`: Bad Request
- `404`: Not Found
- `500`: Internal Server Error

## Architecture

The API is built with:

- **Flask-OpenAPI3**: Provides automatic OpenAPI documentation generation
- **Pydantic**: Request/response validation and schema generation
- **Threading**: Asynchronous operation execution
- **YAML**: Configuration file management

### Directory Structure

```
attack_range/
├── api/                    # API application code
├── config/                 # Saved attack range configs ({attack_range_id}.yml)
├── wireguard_config/       # WireGuard VPN configs ({attack_range_id}.conf)
├── templates/              # Attack range templates
│   ├── aws/
│   ├── azure/
│   └── gcp/
└── terraform/              # Terraform infrastructure code
```

### Key Components

- `app.py`: Main Flask application with route definitions
- `models.py`: Pydantic models for request/response validation
- `requirements.txt`: API-specific dependencies

### Operation Flow

1. Client sends a build/destroy request
2. API validates the request using Pydantic models
3. Configuration is saved (if needed)
4. Operation is queued and starts in a background thread
5. Client receives operation ID
6. Client polls operation status until completion

## Security Considerations

⚠️ **Important**: This API is designed for internal use and does not include authentication/authorization by default.

For production deployments, consider:

- Adding authentication (API keys, OAuth, etc.)
- Enabling HTTPS/TLS
- Implementing rate limiting
- Restricting network access
- Validating and sanitizing user input
- Using environment variables for sensitive configuration

## Troubleshooting

### API won't start

- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that port 4000 is not already in use
- Verify Python version is 3.8+

### Build/Destroy operations fail

- Check the operation status endpoint for error details
- Review the main Attack Range logs in `attack_range.log`
- Ensure cloud provider credentials are properly configured
- Verify terraform and ansible are installed and accessible

### OpenAPI documentation not loading

- Access the JSON directly: `http://localhost:4000/openapi/openapi.json`
- Try different browsers or clear cache
- Check browser console for JavaScript errors

## Contributing

Contributions are welcome! Please follow the project's contribution guidelines.

## License

See the main project LICENSE file.
