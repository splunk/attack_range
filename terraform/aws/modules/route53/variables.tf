variable "vpc_id" {
  description = "The ID of a VPC to associate with the certificate."
  type        = string
  default     = null
}

variable "dns_zone" {
  description = "The DNS zone to create"
  type        = string
  default     = null
}

variable "domain" {
  description = "The domain name to use for the certificate."
  type        = string
  default     = null
}