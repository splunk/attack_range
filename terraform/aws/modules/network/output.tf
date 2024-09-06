output "sg_vpc_id" {
  value = aws_security_group.default.id
}

output "vpc_id" {
  value = var.aws.create_vpc == "1" ? module.vpc[0].vpc_id : var.aws.vpc_id
}

output "ec2_subnet_id" {
  value = var.aws.create_vpc == "1" ? module.vpc[0].public_subnets[0].id : var.aws.public_subnet_id
}
