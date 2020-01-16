
output "vpc_security_group_ids" {
  value = "${aws_security_group.default.id}"
}

output "vpc_subnet_id" {
  value = "${aws_subnet.subnet.id}"
}
