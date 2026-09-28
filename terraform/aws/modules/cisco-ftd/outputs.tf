output "instance_id" {
  description = "ID of the FTDv instance."
  value       = aws_instance.this.id
}

output "mgmt_private_ip" {
  description = "Management private IP of the FTDv instance."
  value       = var.mgmt_private_ip
}

output "inside_private_ip" {
  description = "Inside private IP of the FTDv instance."
  value       = var.inside_private_ip
}

output "outside_private_ip" {
  description = "Outside private IP of the FTDv instance."
  value       = var.outside_private_ip
}

output "inside_eni_id" {
  description = "Inside ENI ID used as the next hop for inspected hosts."
  value       = aws_network_interface.inside.id
}

output "outside_eni_id" {
  description = "Outside ENI ID used as the next hop from mgmt/VPN back to inside hosts."
  value       = aws_network_interface.outside.id
}
