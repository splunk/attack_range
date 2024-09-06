output "instance_id" {
  description = "The instance id of the heavy forwarder"
  value       = aws_instance.httpd_server[0].id
}

output "private_ip" {
  description = "The private IP address of the heavy forwarder (needed for SSH through bastion host)"
  value       = aws_instance.httpd_server[0].private_ip
}
