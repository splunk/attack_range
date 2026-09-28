variable "attack_range_id" {
  description = "Attack Range ID (UUID)"
  type        = string
}

variable "cisco_ftd_enabled" {
  description = "Create extra private subnets in the same AZ for Cisco FTDv interfaces."
  type        = bool
  default     = false
}