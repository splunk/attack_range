
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


variable "kali_ami" {
  type    = string
  default = "ami-0efaa1daf599f3b8e"
}

variable "vpc_security_group_ids" { }

variable "vpc_subnet0_id" { }

variable "kali-machine" {
  default = "0"
}
