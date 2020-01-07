
output "vpc_security_group_ids" {
  value = "${aws_security_group.default.id}"
}

output "vpc_subnet1_id" {
  value = "${aws_subnet.default.1.id}"
}

output "vpc_subnet0_id" {
  value = "${aws_subnet.default.0.id}"
}
