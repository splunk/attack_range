
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

variable "vpc_security_group_ids" { }

variable "vpc_subnet1_id" { }
