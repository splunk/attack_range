
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "public_subnet_id" {
  value = module.vpc.public_subnets[0]
}

output "private_subnet_id" {
  value = module.vpc.private_subnets[0]
}

output "cisco_diag_subnet_id" {
  value = var.cisco_ftd_enabled ? aws_subnet.cisco_diag[0].id : null
}

output "cisco_outside_subnet_id" {
  value = var.cisco_ftd_enabled ? aws_subnet.cisco_outside[0].id : null
}

output "cisco_inside_subnet_id" {
  value = var.cisco_ftd_enabled ? aws_subnet.cisco_inside[0].id : null
}

output "public_route_table_id" {
  value = module.vpc.public_route_table_ids[0]
}

output "private_route_table_id" {
  value = module.vpc.private_route_table_ids[0]
}
