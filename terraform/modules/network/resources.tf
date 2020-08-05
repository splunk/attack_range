

data "aws_availability_zones" "available" {}

locals {
  cluster_name = "cluster_${var.config.key_name}"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "2.44.0"

  name                 = "vpc_${var.config.key_name}"
  cidr                 = "10.0.0.0/16"
  azs                  = data.aws_availability_zones.available.names
  public_subnets      = ["10.0.1.0/24"]
  enable_dns_hostnames = true

}


resource "aws_security_group" "default" {
  name        = "sg_public_subnets_${var.config.key_name}"
  vpc_id      = module.vpc.vpc_id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = concat(var.config.ip_whitelist, ["10.0.0.0/16"])
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["0.0.0.0/0"]
  }
}
