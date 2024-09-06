
variable "nlb_security_group_id" {
  description = "The security group id to use for the load balancer"
  type        = string
}

variable "edge-processor_instance_id" {
  description = "The instance id of the heavy forwarder"
  type        = string
}

variable "aws" {}
variable "edge_processor" {}
variable "general" {}
variable "ec2_subnet_id" {}
