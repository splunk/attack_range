provider "aws" {
  profile    = var.aws_profile
  region     = var.aws_region
}

resource "aws_vpc" "default" {
  cidr_block = "10.0.0.0/16"
}


# Create an internet gateway to give our subnet access to the outside world
resource "aws_internet_gateway" "default" {
  vpc_id = "${aws_vpc.default.id}"
}

# Grant the VPC internet access on its main route table
resource "aws_route" "internet_access" {
  route_table_id         = "${aws_vpc.default.main_route_table_id}"
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = "${aws_internet_gateway.default.id}"
}

# Create a subnet to launch our instances into
resource "aws_subnet" "default" {
  vpc_id                  = "${aws_vpc.default.id}"
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
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

resource "aws_instance" "splunk-server" {
  ami           = var.splunk_ami
  instance_type = "t2.xlarge"
  key_name = var.key_name
  subnet_id = "${aws_subnet.default.id}"
  vpc_security_group_ids = ["${aws_security_group.default.id}"]
  tags = {
    Name = "attack-range_splunk-server"
  }

 provisioner "local-exec" {
    working_dir = "../ansible"
    command = "sleep 30; ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.private_key_path} -i '${aws_instance.splunk-server.public_ip},' playbooks/splunk_server.yml"
  }
}

resource "aws_eip" "ip" {
  instance = aws_instance.splunk-server.id
}
