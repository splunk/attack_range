
data "aws_availability_zones" "available" {}

locals {
  cluster_name = "ar_cluster_${var.attack_range_id}"
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "ar_vpc_${var.attack_range_id}"
  cidr = "10.0.0.0/16"
  azs  = data.aws_availability_zones.available.names

  # One public and one private subnet
  public_subnets  = ["10.0.1.0/24"]
  private_subnets = ["10.0.2.0/24"]

  # DNS + NAT for private subnet internet access
  enable_dns_hostnames = true
  enable_nat_gateway   = true
  single_nat_gateway   = true
}

# FTDv needs four NICs in the same AZ. Extra subnets stay off the VPC module's
# private_subnets list so they are not spread across availability zones.
resource "aws_subnet" "cisco_diag" {
  count             = var.cisco_ftd_enabled ? 1 : 0
  vpc_id            = module.vpc.vpc_id
  cidr_block        = "10.0.3.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "ar_cisco_diag_${var.attack_range_id}"
  }
}

resource "aws_subnet" "cisco_outside" {
  count             = var.cisco_ftd_enabled ? 1 : 0
  vpc_id            = module.vpc.vpc_id
  cidr_block        = "10.0.4.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "ar_cisco_outside_${var.attack_range_id}"
  }
}

resource "aws_subnet" "cisco_inside" {
  count             = var.cisco_ftd_enabled ? 1 : 0
  vpc_id            = module.vpc.vpc_id
  cidr_block        = "10.0.5.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "ar_cisco_inside_${var.attack_range_id}"
  }
}

resource "aws_route_table_association" "cisco_diag" {
  count          = var.cisco_ftd_enabled ? 1 : 0
  subnet_id      = aws_subnet.cisco_diag[0].id
  route_table_id = module.vpc.private_route_table_ids[0]
}

resource "aws_route_table_association" "cisco_outside" {
  count          = var.cisco_ftd_enabled ? 1 : 0
  subnet_id      = aws_subnet.cisco_outside[0].id
  route_table_id = module.vpc.public_route_table_ids[0]
}
