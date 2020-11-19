
data "aws_availability_zones" "available" {}

locals {
  cluster_name = "${var.config.range_name}_cluster_${var.config.key_name}"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "2.44.0"

  name                 = "${var.config.range_name}_vpc_${var.config.key_name}"
  cidr                 = "10.0.0.0/16"
  azs                  = data.aws_availability_zones.available.names
  public_subnets       = ["10.0.1.0/24"]
  enable_dns_hostnames = true

}


resource "aws_security_group" "default" {
  name   = "${var.config.range_name}_sg_public_subnets_${var.config.key_name}"
  vpc_id = module.vpc.vpc_id

  ingress {
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_blocks = ["10.0.0.0/16"]
    }

   ingress {
      from_port   = -1
      to_port     = -1
      protocol    = "icmp"
      cidr_blocks = split(",", var.config.ip_whitelist)
    }

   ingress {
      from_port   = 22
      to_port     = 22
      protocol    = "tcp"
      cidr_blocks = split(",", var.config.ip_whitelist)
    }

   ingress {
      from_port   = 8000
      to_port     = 8000
      protocol    = "tcp"
      cidr_blocks = split(",", var.config.ip_whitelist)
    }

    ingress {
      from_port   = 9997
      to_port     = 9997
      protocol    = "tcp"
      cidr_blocks = split(",", var.config.ip_whitelist)
    }

    ingress {
      from_port   = 8089
      to_port     = 8089
      protocol    = "tcp"
      cidr_blocks = split(",", var.config.ip_whitelist)
    }

   ingress {
    from_port   = 5986
    to_port     = 5986
    protocol    = "tcp"
    cidr_blocks = split(",", var.config.ip_whitelist)
   }

    ingress {
    from_port   = 5985
    to_port     = 5985
    protocol    = "tcp"
    cidr_blocks = split(",", var.config.ip_whitelist)
   }

  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = split(",", var.config.ip_whitelist)
  }

  ingress {
    from_port   = 3389
    to_port     = 3389
    protocol    = "udp"
    cidr_blocks = split(",", var.config.ip_whitelist)
  }


    ingress {
      from_port   = 8888
      to_port     = 8888
      protocol    = "tcp"
      cidr_blocks = split(",", var.config.ip_whitelist)
    }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = split(",", var.config.ip_whitelist)
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
