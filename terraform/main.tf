provider "aws" {
  profile    = var.aws_profile
  region     = var.aws_region
}

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

# standup splunk server
 resource "aws_instance" "splunk-server" {
  ami           = var.splunk_ami
  instance_type = "t2.2xlarge"
  key_name = var.key_name
  subnet_id = "${aws_subnet.default.1.id}"
  vpc_security_group_ids = ["${aws_security_group.default.id}"]
  root_block_device {
    volume_type = "gp2"
    volume_size = "30"
    delete_on_termination = "true"
  }
  tags = {
    Name = "attack-range_splunk-server"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = "${aws_instance.splunk-server.public_ip}"
      private_key = "${file(var.private_key_path)}"
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.private_key_path} -i '${aws_instance.splunk-server.public_ip},' playbooks/splunk_server.yml"
  }
}

resource "aws_eip" "splunk_ip" {
  instance = aws_instance.splunk-server.id
}

resource "aws_ebs_volume" "win2016_volume" {
  availability_zone = "us-west-2a"
  size              = 50

}


# standup windows 2016 domain controller
resource "aws_instance" "windows_2016_dc" {
  ami           = var.windows_2016_dc_ami
  instance_type = "t2.2xlarge"
  key_name = var.key_name
  subnet_id = "${aws_subnet.default.0.id}"
  vpc_security_group_ids = ["${aws_security_group.default.id}"]
  tags = {
    Name = "attack-range_windows_2016_dc"
  }
  user_data = <<EOF
<powershell>
$admin = [adsi]("WinNT://./${var.win_username}, user")
$admin.PSBase.Invoke("SetPassword", "${var.win_password}")
Invoke-Expression ((New-Object System.Net.Webclient).DownloadString('https://raw.githubusercontent.com/ansible/ansible/devel/examples/scripts/ConfigureRemotingForAnsible.ps1'))
</powershell>
EOF

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type     = "winrm"
      user     = "${var.win_username}"
      password = "${var.win_password}"
      host     = "${aws_instance.windows_2016_dc.public_ip}"
      port     = 5986
      insecure = true
      https    = true
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "sed -i '' 's/PUBLICIP/${aws_instance.windows_2016_dc.public_ip}/g' inventory/hosts;ansible-playbook -i inventory/hosts playbooks/windows_dc.yml --extra-vars 'splunk_indexer_ip=${aws_instance.splunk-server.private_ip}'"
  }

}


output "splunk_server" {
  value = "http://${aws_eip.splunk_ip.public_ip}:8000"
}

output "windows_dc_user" {
  value = "${var.win_username}"
}

output "windows_dc_password" {
  value = "${var.win_password}"
}
