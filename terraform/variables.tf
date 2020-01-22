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
}

variable "win_password" {
	description = "Windows Host default password to use"
	type = "string"
}

variable "key_name" {
  description = "Desired name of AWS key pair"
}


variable "ip_whitelist" {
  description = "A list of CIDRs that will be allowed to access the EC2 instances"
  type        = list(string)
}


#environment variables
variable "windows_domain_controller" {
  default = "1"
}

variable "windows_server" {
  default = "0"
}

variable "kali_machine" {
  default = "0"
}

variable "splunk_server_private_ip" { }
variable "windows_domain_controller_private_ip" { }
variable "windows_domain_controller_os" { }
variable "windows_server_os" { }
variable "windows_server_private_ip" { }
variable "windows_server_join_domain" { }
variable "kali_machine_private_ip" { }


#ansible variables
# ---------------------- #
# general
variable "region" { }
variable "availability_zone" { }
variable "subnet_cidr" { }

# Splunk server
variable "splunk_admin_password" { }
variable "splunk_url" { }
variable "splunk_binary" { }
variable "s3_bucket_url" { }
variable "splunk_escu_app" { }
variable "splunk_asx_app" { }
variable "splunk_windows_ta" { }
variable "splunk_cim_app" { }
variable "splunk_sysmon_ta" { }

# Windows server
variable "splunk_uf_win_url" { }
variable "win_sysmon_url" { }
variable "win_sysmon_template" { }
