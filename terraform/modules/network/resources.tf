
# provider "aws" {
#   profile    = "{var.aws_profile}"
#   region     = "${var.aws_region}"
# }

resource "aws_vpc" "default" {
  cidr_block = "${var.vpc_cidr}"
}


# Create an internet gateway to give our subnet access to the outside world
resource "aws_internet_gateway" "default" {
  vpc_id = "${aws_vpc.default.id}"
}

# Create a subnet to launch our instances into
resource "aws_subnet" "default" {
  count                   = "${length(var.subnets)}"
  vpc_id                  = "${aws_vpc.default.id}"
  cidr_block              = "${element(values(var.subnets), count.index)}"
  map_public_ip_on_launch = true
  availability_zone       = "${element(keys(var.subnets), count.index)}"
  depends_on              = ["aws_internet_gateway.default"]
}

# Grant the VPC internet access on its main route table
resource "aws_route" "internet_access" {
  route_table_id         = "${aws_vpc.default.main_route_table_id}"
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = "${aws_internet_gateway.default.id}"
}

resource "aws_security_group" "default" {
  name        = "allow_whitelist"
  description = "Allow all inbound traffic from whilisted IPs in vars file of terraform attack range"
  vpc_id      = "${aws_vpc.default.id}"
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = var.ip_whitelist
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["0.0.0.0/0"]
  }
}
