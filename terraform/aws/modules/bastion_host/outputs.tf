output "security_group_id" {
  description = "The id of the security group"
  value = aws_security_group.main.id
}

output "public_ip" {
  description = "The public ip address of the bastion host"
  value = aws_instance.bastion_host.public_ip
}
