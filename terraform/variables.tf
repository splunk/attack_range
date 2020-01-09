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

variable "aws_region" {
  description = "AWS region to launch servers. Default to us-west-2"
  default     = "us-west-2"
}

# for automatic availability zone selection see:
# https://dwmkerr.com/dynamic-and-configurable-availability-zones-in-terraform/
variable "vpc_cidr" {
  description = "The CIDR block for the VPC, e.g: 10.0.0.0/16"
  type = "string"
  default = "10.0.0.0/16"
}

# remember to change the default subnet ID under main.tf:
# subnet_id = "${aws_subnet.default.0.id}" where 0 to 2 is your subnet number below
variable "subnets" {
  description = "A map of availability zones to CIDR blocks, which will be set up as subnets."
  type = "map"
  default = {
    us-west-2a = "10.0.1.0/24"
    us-west-2b = "10.0.2.0/24"
    us-west-2c = "10.0.3.0/24"
  }
}

variable "aws_profile" {
  default = "default"
}

variable "ip_whitelist" {
  description = "A list of CIDRs that will be allowed to access the EC2 instances"
  type        = list(string)
  default     = [""]
}


# The default values for us-west-2 have been provied for you
# You will have to change the default values if you use a different region

# uses ubuntu 18.04 at the moment
variable "splunk_ami" {
  type    = string
  default = "ami-005bdb005fb00e791"
}

# uses AWS AMI Windows 2016 Server Base
# See https://aws.amazon.com/marketplace/server/configuration?productId=13c2dbc9-57fc-4958-922e-a1ba7e223b0d for details
variable "windows_2016_dc_ami" {
  type    = string
  default = "ami-0df99cdd65bce4245"
}

variable "kali_ami" {
  type    = string
  default = "ami-0efaa1daf599f3b8e"
}


variable "splunk_server_private_ip" {
  type    = string
  default = "10.0.2.10"
}

variable "windows_dc_server_private_ip" {
  type    = string
  default = "10.0.1.5"
}


#environment variables
variable "windows_2016_dc" {
  default = "1"
}

variable "windows_2016_dc_client" {
  default = "0"
}

variable "kali-machine" {
  default = "0"
}
