locals {
  windows_user_data_template = <<EOF
<powershell>
$admin = [adsi]("WinNT://./%USERNAME%, user")
$admin.PSBase.Invoke("SetPassword", "${var.general.attack_range_password}")

# Stop WinRM service first
net stop winrm

# Configure WinRM from scratch
winrm quickconfig -q
winrm set winrm/config '@{MaxTimeoutms="1800000"}'
winrm set winrm/config/winrs '@{MaxMemoryPerShellMB="1024"}'
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
winrm set winrm/config/service/auth '@{Basic="true"}'
winrm set winrm/config/client/auth '@{Basic="true"}'
winrm set winrm/config/listener?Address=*+Transport=HTTP '@{Port="5985"}'

# Configure firewall rules
netsh advfirewall firewall add rule name="WinRM 5985" protocol=TCP dir=in localport=5985 action=allow
netsh advfirewall firewall add rule name="WinRM 5986" protocol=TCP dir=in localport=5986 action=allow

# Enable PSRemoting and skip network profile check
Enable-PSRemoting -SkipNetworkProfileCheck -Force

# Configure WinRM service
sc.exe config winrm start=auto
net start winrm

# Enable RDP
Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -name "fDenyTSConnections" -value 0

# Extend C drive
$drive_letter = "C"
$size = (Get-PartitionSupportedSize -DriveLetter $drive_letter)
Resize-Partition -DriveLetter $drive_letter -Size $size.SizeMax
</powershell>
EOF

  linux_user_data_template = <<EOF
#!/bin/bash
set -e
# Set password for %USERNAME% user
# Create a temporary file to avoid shell quoting issues with special characters
TMPFILE=$(mktemp)
echo '%USERNAME%:%PASSWORD%' > "$TMPFILE"
/usr/sbin/chpasswd < "$TMPFILE"
rm -f "$TMPFILE"

# Verify password was set
if [ $? -eq 0 ]; then
  echo "Password set successfully for %USERNAME%"
else
  echo "Failed to set password for %USERNAME%" >&2
  exit 1
fi

# Unlock the user account (important for Ubuntu cloud images)
usermod -U %USERNAME% 2>/dev/null || true

# Remove password expiration
chage -E -1 -m 0 -M 99999 -I -1 -W 7 %USERNAME% 2>/dev/null || passwd -u %USERNAME% 2>/dev/null || true

# Create a higher priority SSH config file to override cloud-init settings
# Cloud-init creates /etc/ssh/sshd_config.d/60-cloudimg-settings.conf which disables password auth
# We create 99-enable-password.conf which loads after it and overrides those settings
cat > /etc/ssh/sshd_config.d/99-enable-password.conf <<'SSHCONF'
PasswordAuthentication yes
KbdInteractiveAuthentication yes
PubkeyAuthentication yes
UsePAM yes
SSHCONF

# Ensure the config directory exists and has correct permissions
chmod 644 /etc/ssh/sshd_config.d/99-enable-password.conf

# Restart SSH service
systemctl restart sshd || service ssh restart

# Wait a moment for SSH to fully restart
sleep 2

# Verify the configuration
echo "SSH PasswordAuthentication (effective): $(sshd -T | grep -i passwordauthentication || echo 'check failed')"
echo "User %USERNAME% account status: $(passwd -S %USERNAME% 2>/dev/null || echo 'unknown')"
EOF


  # AMI map - dynamically created from attack_range configuration
  ami_map = {
    for k, v in data.aws_ami.dynamic : k => v.id
  }

  # Check if zeek server should be enabled (if there's a server with zeek: true or name == "zeek")
  zeek_server_enabled = length([
    for server in var.attack_range : server
    if try(server.zeek, false) || server.name == "zeek"
  ]) > 0

  # Find the zeek server configuration
  zeek_server_config = try(
    [for server in var.attack_range : server if try(server.zeek, false) || server.name == "zeek"][0],
    null
  )

  # Create a map of server names to session numbers for zeek monitoring
  zeek_session_numbers = {
    for idx, server in var.attack_range :
    server.name => 100 + idx
    if try(server.zeek_monitor, false)
  }

  cisco_fmc_servers = {
    for server in var.attack_range : server.name => server
    if try(server.cisco_fmc, false)
  }

  cisco_ftd_servers = {
    for server in var.attack_range : server.name => server
    if try(server.cisco_ftd, false)
  }

  cisco_ftd_enabled = length(local.cisco_ftd_servers) > 0

  cisco_fmc_ip = length(local.cisco_fmc_servers) > 0 ? "10.0.2.${values(local.cisco_fmc_servers)[0].ip_last_octet}" : ""

  # Optional per-server network: mgmt/private (10.0.2), inside (10.0.5), outside (10.0.4), diag (10.0.3).
  server_network_third_octet = {
    mgmt    = 2
    private = 2
    diag    = 3
    outside = 4
    inside  = 5
  }
}

# Dynamic AMI data source - uses ami_name_filter and ami_owner from attack_range configuration
data "aws_ami" "dynamic" {
  for_each = {
    for server in var.attack_range : server.name => server
    if try(server.ami_name_filter, null) != null && try(server.ami_owner, null) != null
  }
  most_recent = true
  owners      = [each.value.ami_owner]

  filter {
    name   = "name"
    values = [each.value.ami_name_filter]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  dynamic "filter" {
    for_each = try(each.value.ami_product_code, null) != null ? [each.value.ami_product_code] : []
    content {
      name   = "product-code"
      values = [filter.value]
    }
  }
}

# Data source for router Ubuntu AMI (always Ubuntu Jammy 22.04)
data "aws_ami" "router_ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Data source for Zeek server AMI (uses the zeek server's configuration from attack_range)
# The AMI will be looked up from the existing ami_map using the zeek server's name

module "networkModule" {
  source            = "./modules/network"
  attack_range_id   = var.general.attack_range_id
  cisco_ftd_enabled = local.cisco_ftd_enabled
}

module "router" {
  source          = "./modules/router"
  subnet_id       = module.networkModule.public_subnet_id
  ami_id          = data.aws_ami.router_ubuntu.id
  attack_range_id = var.general.attack_range_id
  vpc_id          = module.networkModule.vpc_id
  key_name        = var.general.key_name
  private_ip      = "10.0.1.10"
  ip_whitelist    = var.general.ip_whitelist
}

# Zeek server module (created before attack_range_servers to provide filter/target IDs)
# Uses the zeek server configuration from attack_range when zeek: true is set
module "zeek_server" {
  source = "./modules/zeek-server"

  zeek_server           = local.zeek_server_enabled
  ami_id                = local.zeek_server_config != null ? local.ami_map[local.zeek_server_config.name] : ""
  instance_type         = local.zeek_server_config != null ? local.zeek_server_config.instance_type : "m5.2xlarge"
  key_name              = local.zeek_server_config != null && !try(local.zeek_server_config.windows, false) ? var.general.key_name : null
  subnet_id             = module.networkModule.private_subnet_id
  private_ip            = local.zeek_server_config != null ? "10.0.2.${local.zeek_server_config.ip_last_octet}" : "10.0.2.50"
  attack_range_id       = var.general.attack_range_id
  attack_range_password = var.general.attack_range_password
  server_name           = local.zeek_server_config != null ? local.zeek_server_config.name : "zeek"
  vpc_id                = module.networkModule.vpc_id
}

module "cisco_fmc" {
  source   = "./modules/cisco-fmc"
  for_each = local.cisco_fmc_servers

  server_name                       = each.value.name
  attack_range_id                   = var.general.attack_range_id
  ami_id                            = local.ami_map[each.value.name]
  instance_type                     = each.value.instance_type
  key_name                          = var.general.key_name
  subnet_id                         = module.networkModule.private_subnet_id
  private_ip                        = "10.0.2.${each.value.ip_last_octet}"
  vpc_id                            = module.networkModule.vpc_id
  admin_password                    = var.general.attack_range_password
  hostname                          = try(each.value.hostname, each.value.name)
  root_volume_size                  = try(each.value.root_volume_size, 250)
  root_volume_type                  = try(each.value.root_volume_type, "gp3")
  root_volume_encrypted             = try(each.value.root_volume_encrypted, true)
  root_volume_delete_on_termination = try(each.value.root_volume_delete_on_termination, true)
}

module "cisco_ftd" {
  source   = "./modules/cisco-ftd"
  for_each = local.cisco_ftd_servers

  server_name                       = each.value.name
  attack_range_id                   = var.general.attack_range_id
  ami_id                            = local.ami_map[each.value.name]
  instance_type                     = each.value.instance_type
  key_name                          = var.general.key_name
  vpc_id                            = module.networkModule.vpc_id
  mgmt_subnet_id                    = module.networkModule.private_subnet_id
  diag_subnet_id                    = module.networkModule.cisco_diag_subnet_id
  outside_subnet_id                 = module.networkModule.cisco_outside_subnet_id
  inside_subnet_id                  = module.networkModule.cisco_inside_subnet_id
  mgmt_private_ip                   = "10.0.2.${each.value.ip_last_octet}"
  diag_private_ip                   = "10.0.3.${try(each.value.diag_ip_last_octet, each.value.ip_last_octet)}"
  outside_private_ip                = "10.0.4.${try(each.value.outside_ip_last_octet, each.value.ip_last_octet)}"
  inside_private_ip                 = "10.0.5.${try(each.value.inside_ip_last_octet, each.value.ip_last_octet)}"
  admin_password                    = var.general.attack_range_password
  hostname                          = try(each.value.hostname, each.value.name)
  fmc_ip                            = local.cisco_fmc_ip
  reg_key                           = try(each.value.reg_key, "cisco")
  nat_id                            = try(each.value.nat_id, "cisco")
  root_volume_size                  = try(each.value.root_volume_size, 120)
  root_volume_type                  = try(each.value.root_volume_type, "gp3")
  root_volume_encrypted             = try(each.value.root_volume_encrypted, true)
  root_volume_delete_on_termination = try(each.value.root_volume_delete_on_termination, true)

  depends_on = [module.cisco_fmc]
}

resource "aws_eip" "cisco_ftd_outside" {
  count             = local.cisco_ftd_enabled ? 1 : 0
  domain            = "vpc"
  network_interface = values(module.cisco_ftd)[0].outside_eni_id
  tags = {
    Name = "ar-ftd-outside-${var.general.attack_range_id}"
  }
  depends_on = [module.cisco_ftd]
}

resource "aws_route_table" "cisco_inside" {
  count  = local.cisco_ftd_enabled ? 1 : 0
  vpc_id = module.networkModule.vpc_id

  tags = {
    Name = "ar-cisco-inside-${var.general.attack_range_id}"
  }
}

resource "aws_route" "cisco_inside_default" {
  count                  = local.cisco_ftd_enabled ? 1 : 0
  route_table_id         = aws_route_table.cisco_inside[0].id
  destination_cidr_block = "0.0.0.0/0"
  network_interface_id   = values(module.cisco_ftd)[0].inside_eni_id
}

# Windows -> Splunk/FMC is inspected. Do not steer 10.0.1.0/24 here or WinRM/RDP
# return traffic hairpins through an undeployed FTD.
resource "aws_route" "cisco_inside_mgmt" {
  count                  = local.cisco_ftd_enabled ? 1 : 0
  route_table_id         = aws_route_table.cisco_inside[0].id
  destination_cidr_block = "10.0.2.0/24"
  network_interface_id   = values(module.cisco_ftd)[0].inside_eni_id
}

resource "aws_route_table_association" "cisco_inside" {
  count          = local.cisco_ftd_enabled ? 1 : 0
  subnet_id      = module.networkModule.cisco_inside_subnet_id
  route_table_id = aws_route_table.cisco_inside[0].id
}

# Splunk/FMC return path to inside hosts goes through FTD. VPN/WinRM/RDP stay
# on the VPC local route so Ansible can reach Windows before the first deploy.
resource "aws_route" "private_to_inside" {
  count                  = local.cisco_ftd_enabled ? 1 : 0
  route_table_id         = module.networkModule.private_route_table_id
  destination_cidr_block = "10.0.5.0/24"
  network_interface_id   = values(module.cisco_ftd)[0].outside_eni_id
}

# Dynamic module creation based on attack_range configuration
# Exclude zeek servers (they are handled by the zeek_server module)
# Exclude Cisco FMC/FTD (they need marketplace day-0 config and extra NICs)
module "attack_range_servers" {
  source = "./modules/generic-server"
  for_each = {
    for server in var.attack_range : server.name => server
    if !try(server.zeek, false) && server.name != "zeek" && !try(server.cisco_fmc, false) && !try(server.cisco_ftd, false)
  }

  server_name                   = each.value.name
  attack_range_id               = var.general.attack_range_id
  attack_range_password         = var.general.attack_range_password
  ami_id                        = local.ami_map[each.value.name]
  instance_type                 = each.value.instance_type
  key_name                      = try(each.value.windows, false) ? null : var.general.key_name
  subnet_id                     = try(each.value.network, "mgmt") == "inside" ? module.networkModule.cisco_inside_subnet_id : (try(each.value.network, "mgmt") == "outside" ? module.networkModule.cisco_outside_subnet_id : (try(each.value.network, "mgmt") == "diag" ? module.networkModule.cisco_diag_subnet_id : module.networkModule.private_subnet_id))
  private_ip                    = "10.0.${lookup(local.server_network_third_octet, try(each.value.network, "mgmt"), 2)}.${each.value.ip_last_octet}"
  vpc_id                        = module.networkModule.vpc_id
  user_data                     = try(each.value.windows, false) == true ? replace(local.windows_user_data_template, "%USERNAME%", try(each.value.user_name, "Administrator")) : replace(replace(local.linux_user_data_template, "%USERNAME%", try(each.value.user_name, "ubuntu")), "%PASSWORD%", var.general.attack_range_password)
  zeek_monitor                  = try(each.value.zeek_monitor, false)
  zeek_traffic_mirror_filter_id = local.zeek_server_enabled ? module.zeek_server.traffic_mirror_filter_id : null
  zeek_traffic_mirror_target_id = local.zeek_server_enabled ? module.zeek_server.traffic_mirror_target_id : null
  zeek_session_number           = try(local.zeek_session_numbers[each.value.name], null)

  depends_on = [
    module.cisco_ftd,
    aws_route_table_association.cisco_inside,
  ]
}