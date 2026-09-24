variable "ami_id" {
  description = "Cisco FMCv marketplace AMI ID."
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type. Cisco recommends c5.4xlarge for FMCv."
  type        = string
  default     = "c5.4xlarge"
}

variable "key_name" {
  description = "SSH key name."
  type        = string
  default     = null
}

variable "subnet_id" {
  description = "Management subnet ID."
  type        = string
}

variable "private_ip" {
  description = "Management private IP."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for the security group."
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
  description = "FMC admin password applied via day-0 configuration."
  type        = string
  sensitive   = true
}

variable "hostname" {
  description = "Hostname set in FMC day-0 configuration."
  type        = string
  default     = "fmc"
}

variable "root_volume_type" {
  description = "Root volume type."
  type        = string
  default     = "gp3"
}

variable "root_volume_size" {
  description = "Root volume size in GB. FMCv requires at least 250 GB."
  type        = number
  default     = 250
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
