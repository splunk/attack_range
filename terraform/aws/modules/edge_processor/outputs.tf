output "instance_id" {
  description = "The instance id of the edge processor"
  value       = aws_instance.edge_processor[0].id
}

output "private_ip" {
  description = "The private IP address of the edge processor (needed for SSH through bastion host)"
  value       = aws_instance.edge_processor[0].private_ip
}
