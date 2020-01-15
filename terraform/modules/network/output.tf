
output "vpc_security_group_ids" {
  value = "${aws_security_group.default.id}"
}

output "vpc_subnet_one_id" {
  value = "${aws_subnet.subnet_one.id}"
}

output "vpc_subnet_two_id" {
  value = "${aws_subnet.subnet_two.id}"
}
