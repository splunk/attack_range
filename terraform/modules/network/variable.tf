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

variable "aws_region" {
  description = "AWS region to launch servers. Default to us-west-2"
  default     = "us-west-2"
}

variable "ip_whitelist" {
  description = "A list of CIDRs that will be allowed to access the EC2 instances"
  type        = list(string)
  default     = [""]
}
