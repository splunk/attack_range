
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
	type = string
}

variable "win_password" {
	description = "Windows Host default password to use"
	type = string
}

variable "key_name" {
  description = "Desired name of AWS key pair"
}

variable "windows_domain_controller_instance" { }
variable "windows_domain_controller_instance_packer" { }

variable "vpc_security_group_ids" { }

variable "ec2_subnet_id" { }

variable "windows_server" { }

variable "splunk_server_private_ip" { }
variable "windows_domain_controller_private_ip" { }
variable "windows_server_private_ip" { }
variable "windows_server_os" { }
variable "windows_server_join_domain" { }

variable "use_packer_amis" { }
variable "windows_server_packer_ami" { }

# Ansible vars
# Windows server
variable "splunk_uf_win_url" { }
variable "win_sysmon_url" { }
variable "win_sysmon_template" { }
variable "splunk_admin_password" { }

variable "splunk_stream_app" { }
variable "s3_bucket_url" { }

variable "run_demo" { }
variable "demo_scenario" { }
