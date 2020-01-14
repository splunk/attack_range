
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


variable "key_name" {
  description = "Desired name of AWS key pair"
}


# uses ubuntu 18.04 at the moment
variable "splunk_ami" {
  type    = string
  default = "ami-005bdb005fb00e791"
}

variable "splunk_server_private_ip" {
  type    = string
  default = "10.0.2.10"
}

variable "vpc_security_group_ids" { }

variable "vpc_subnet1_id" { }


#ansible variables
# ---------------------- #
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
