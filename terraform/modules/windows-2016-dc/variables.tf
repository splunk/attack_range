
variable "private_key_path" {
  description = <<DESCRIPTION
Path to the SSH private key to be used for authentication.
Ensure this keypair is added to your local SSH agent so provisioners can
connect.

Example: ~/.ssh/terraform.key
Defaults to: ~/.ssh/id_rsa
DESCRIPTION
  default = "~/.ssh/id_rsa"
}

variable "win_username" {
	description = "Windows Host default username to use"
	type = "string"
	default = "Administrator"
}

variable "win_password" {
	description = "Windows Host default password to use"
	type = "string"
}

variable "key_name" {
  description = "Desired name of AWS key pair"
}

variable "vpc_security_group_ids" { }

variable "vpc_subnet_id" { }
variable "availability_zone" { }

variable "windows_2016_dc" { }

variable "splunk_server_private_ip" { }
variable "windows_2016_dc_private_ip" { }

# Ansible vars
# Windows server
variable "splunk_uf_win_url" { }
variable "win_sysmon_url" { }
variable "win_sysmon_template" { }
variable "splunk_admin_password" { }
