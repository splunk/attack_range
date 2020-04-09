
resource "aws_vpc" "vpc_attack_range" {
  cidr_block = var.subnet_vpc
  enable_dns_hostnames = "true"
}


# Create an internet gateway to give our subnet access to the outside world
resource "aws_internet_gateway" "default" {
  vpc_id = aws_vpc.vpc_attack_range.id
}

resource "aws_subnet" "subnet" {
  vpc_id                  = aws_vpc.vpc_attack_range.id
  cidr_block              = var.subnet_ec2
  map_public_ip_on_launch = true
  availability_zone       = var.availability_zone
  depends_on              = [aws_internet_gateway.default]
}

# Grant the VPC internet access on its main route table
resource "aws_route" "internet_access" {
  route_table_id         = aws_vpc.vpc_attack_range.main_route_table_id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.default.id
}

resource "aws_security_group" "default" {
  name        = "allow_whitelist"
  description = "Allow all inbound traffic from whilisted IPs in vars file of terraform attack range"
  vpc_id      = aws_vpc.vpc_attack_range.id
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = concat(var.ip_whitelist, [var.subnet_ec2])
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["0.0.0.0/0"]
  }
}
