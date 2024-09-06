variable "instance_profile_name" {
  description = "A prefix to attach to all resources created by terraform"
  type        = string
}
variable "bastion_host_security_group_id" {
  description = "The id of the security group for the bastion host"
  type        = string
}

variable "elb_security_group_id" {
  description = "The id of the security group for the load balancer if in use"
  type        = string
}

variable "aws" {}
variable "general" {}
variable "httpd_server" {}
variable "splunk_server" {}
