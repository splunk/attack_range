

output "sg_vpc_id" {
  value = aws_security_group.default.id
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "ec2_subnet_id" {
  value = module.vpc.public_subnets[0]
}
