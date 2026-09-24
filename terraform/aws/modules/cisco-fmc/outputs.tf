output "instance_id" {
  description = "ID of the FMCv instance."
  value       = aws_instance.this.id
}

output "private_ip" {
  description = "Management private IP of the FMCv instance."
  value       = var.private_ip
}

output "network_interface_id" {
  description = "Management ENI ID."
  value       = aws_network_interface.mgmt.id
}
