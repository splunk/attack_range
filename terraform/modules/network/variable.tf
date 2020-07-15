

variable "ip_whitelist" {
  description = "A list of CIDRs that will be allowed to access the EC2 instances"
  type        = list(string)
}

variable "key_name" {
  description = "Desired name of AWS key pair"
}
