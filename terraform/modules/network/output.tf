

output "sg_vpc_id" {
  value = aws_security_group.default.id
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "ec2_subnet_id" {
  value = module.vpc.public_subnets[0]
}

output "vpc_private_subnets" {
  value = module.vpc.private_subnets
}

output "sg_worker_group_mgmt_one_id" {
  value = aws_security_group.worker_group_mgmt_one.id
}

output "sg_worker_group_mgmt_two_id" {
  value = aws_security_group.worker_group_mgmt_two.id
}
