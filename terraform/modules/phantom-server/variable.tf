
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

variable "vpc_security_group_ids" { }

variable "vpc_subnet_id" { }

variable "phantom_server" { }
variable "phantom_server_private_ip" { }

variable "use_packer_amis" { }
variable "phantom_packer_ami" { }

#ansible variables
# ---------------------- #

# Phantom server
variable "phantom_admin_password" { }
variable "phantom_community_username" { }
variable "phantom_community_password" { }
