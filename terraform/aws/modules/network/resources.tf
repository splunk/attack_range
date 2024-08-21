
data "aws_availability_zones" "available" {}

locals {
  cluster_name = "cluster_${var.general.key_name}_${var.general.attack_range_name}"
}

# Create VPC if var.aws.create_vpc is set to "1"
module "vpc" {
  count  = var.aws.create_vpc == "1" ? 1 : 0
  source = "terraform-aws-modules/vpc/aws"

  name                 = "vpc_${var.general.key_name}_${var.general.attack_range_name}"
  cidr                 = "10.0.0.0/16"
  azs                  = data.aws_availability_zones.available.names
  public_subnets       = ["10.0.1.0/24"]
  enable_dns_hostnames = true
}

# Use the public subnet from the created VPC or the existing public subnet
locals {
  public_subnet = var.aws.create_vpc == "1" ? module.vpc[0].public_subnets : var.aws.network_cidr
  vpc_id = var.aws.create_vpc == "v1" ? module.vpc[0].vpc_id : var.aws.vpc_ids

resource "aws_security_group" "default" {
  name   = "sg_public_subnets_${var.general.key_name}_${var.general.attack_range_name}"
  vpc_id = local.vpc_id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [local.public_subnet]
  }

  ingress {
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = [local.public_subnet]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 8443
    to_port     = 8443
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 9997
    to_port     = 9997
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 8089
    to_port     = 8089
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 5986
    to_port     = 5986
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 5985
    to_port     = 5985
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "udp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 8888
    to_port     = 8888
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 3391
    to_port     = 3391
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 2323
    to_port     = 2323
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 7999
    to_port     = 7999
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 50051
    to_port     = 50051
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = split(",", var.general.ip_whitelist)
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
