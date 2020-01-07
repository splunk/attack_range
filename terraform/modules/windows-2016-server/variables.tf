
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

variable "splunk_private_ip" {
  description = "private ip of splunk server"
}

variable "vpc_security_group_ids" { }

variable "vpc_subnet0_id" { }
