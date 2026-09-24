variable "ami_id" {
  description = "Cisco FTDv marketplace AMI ID."
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type. Cisco minimum for FTDv is c5.xlarge."
  type        = string
  default     = "c5.xlarge"
}

variable "key_name" {
  description = "SSH key name."
  type        = string
  default     = null
}

variable "vpc_id" {
  description = "VPC ID for the security group."
  type        = string
}

variable "mgmt_subnet_id" {
  description = "Management subnet ID (eth0)."
  type        = string
}

variable "diag_subnet_id" {
  description = "Diagnostic subnet ID (eth1)."
  type        = string
}

variable "outside_subnet_id" {
  description = "Outside/untrust subnet ID (eth2)."
  type        = string
}

variable "inside_subnet_id" {
  description = "Inside/trust subnet ID (eth3)."
  type        = string
}

variable "mgmt_private_ip" {
  description = "Management private IP."
  type        = string
}

variable "diag_private_ip" {
  description = "Diagnostic private IP."
  type        = string
}

variable "outside_private_ip" {
  description = "Outside private IP."
  type        = string
}

variable "inside_private_ip" {
  description = "Inside private IP."
  type        = string
}

variable "server_name" {
  description = "Server name used in resource tags."
  type        = string
}

variable "attack_range_id" {
  description = "Attack Range ID (UUID)."
  type        = string
}

variable "admin_password" {
  description = "FTD admin password applied via day-0 configuration."
  type        = string
  sensitive   = true
}

variable "hostname" {
  description = "Hostname set in FTD day-0 configuration."
  type        = string
  default     = "ftd"
}

variable "fmc_ip" {
  description = "FMC management IP used for device registration. Empty enables local (FDM) management."
  type        = string
  default     = ""
}

variable "reg_key" {
  description = "Registration key shared between FTD and FMC."
  type        = string
  default     = "cisco"
}

variable "nat_id" {
  description = "NAT ID shared between FTD and FMC."
  type        = string
  default     = "cisco"
}

variable "root_volume_type" {
  description = "Root volume type."
  type        = string
  default     = "gp3"
}

variable "root_volume_size" {
  description = "Root volume size in GB. FTDv 10.x marketplace AMIs require at least 103 GB."
  type        = number
  default     = 120
}

variable "root_volume_delete_on_termination" {
  description = "Whether to delete the root volume on instance termination."
  type        = bool
  default     = true
}

variable "root_volume_encrypted" {
  description = "Whether the root volume is encrypted."
  type        = bool
  default     = true
}
