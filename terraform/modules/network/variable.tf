

variable "ip_whitelist" {
  description = "A list of CIDRs that will be allowed to access the EC2 instances"
  type        = list(string)
}

variable "availability_zone" { }
variable "subnet_cidr" { }
