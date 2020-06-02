

data "aws_availability_zones" "available" {}

locals {
  cluster_name = "cluster_${var.key_name}"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "2.6.0"

  name                 = "vpc_${var.key_name}"
  cidr                 = "10.0.0.0/16"
  azs                  = data.aws_availability_zones.available.names
  public_subnets      = ["10.0.1.0/24", "10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
  private_subnets       = ["10.0.14.0/24", "10.0.15.0/24", "10.0.16.0/24"]
  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true

  private_subnet_tags = {
    "kubernetes.io/cluster/kubernetes_${var.key_name}" = "shared"
    "kubernetes.io/role/elb" = "1"
  }
  public_subnet_tags = {
    "kubernetes.io/cluster/kubernetes_${var.key_name}" = "shared"
    "kubernetes.io/role/internal-elb" = "1"
  }
  vpc_tags = {
    "kubernetes.io/cluster/kubernetes_${var.key_name}" = "shared"
  }

}


resource "aws_security_group" "default" {
  name        = "sg_public_subnets_${var.key_name}"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = concat(var.ip_whitelist, ["10.0.0.0/16"])
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "worker_group_mgmt_one" {
  name_prefix = "worker_group_mgmt_one"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"

    cidr_blocks = [
      "10.0.0.0/8",
    ]
  }
}

resource "aws_security_group" "worker_group_mgmt_two" {
  name_prefix = "worker_group_mgmt_two"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"

    cidr_blocks = [
      "192.168.0.0/16",
    ]
  }
}

resource "aws_security_group" "all_worker_mgmt" {
  name_prefix = "all_worker_management"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port = 22
    to_port   = 22
    protocol  = "tcp"

    cidr_blocks = [
      "10.0.0.0/8",
      "172.16.0.0/12",
      "192.168.0.0/16",
    ]
  }
}
