data "aws_ami" "latest-ubuntu" {
  count = var.config.zeek_sensor == "1" ? 1 : 0
  most_recent = true
  owners = ["099720109477"] # Canonical

  filter {
      name   = "name"
      values = ["ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-*"]
  }

  filter {
      name   = "virtualization-type"
      values = ["hvm"]
  }
}

resource "aws_instance" "zeek_sensor" {
  count = var.config.zeek_sensor == "1" ? 1 : 0
  ami           = data.aws_ami.latest-ubuntu[count.index].id
  instance_type = "m5.2xlarge"
  key_name = var.config.key_name
  subnet_id = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip = var.config.zeek_sensor_private_ip
  tags = {
    Name = "aws-${var.config.range_name}-zeek-sensor"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = aws_instance.zeek_sensor[count.index].public_ip
      private_key = file(var.config.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../../ansible/"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.config.private_key_path} -i '${aws_instance.zeek_sensor[0].public_ip},' playbooks/zeek.yml -e 'ansible_python_interpreter=/usr/bin/python3 splunk_uf_url=${var.config.splunk_uf_linux_deb_url} splunk_uf_binary=${var.config.splunk_uf_binary} windows_domain_controller_zeek_capture=${var.config.windows_domain_controller_zeek_capture} windows_server_zeek_capture=${var.config.windows_server_zeek_capture} splunk_indexer_ip=${var.config.splunk_server_private_ip}'"
  }
}

resource "aws_eip" "zeek_ip" {
  count = var.config.zeek_sensor == "1" ? 1 : 0
  instance      = aws_instance.zeek_sensor[0].id
}

resource "aws_ec2_traffic_mirror_target" "zeek_target" {
  count = var.config.zeek_sensor == "1" ? 1 : 0
  description          = "VPC Tap for Zeek"
  network_interface_id = aws_instance.zeek_sensor[0].primary_network_interface_id
}

resource "aws_ec2_traffic_mirror_filter" "zeek_filter" {
  count = var.config.zeek_sensor == "1" ? 1 : 0
  description = "Zeek Mirror Filter - Allow All"
}

resource "aws_ec2_traffic_mirror_filter_rule" "zeek_outbound" {
  count = var.config.zeek_sensor == "1" ? 1 : 0
  description = "Zeek Outbound Rule"
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.zeek_filter[0].id
  destination_cidr_block = "0.0.0.0/0"
  source_cidr_block = "0.0.0.0/0"
  rule_number = 1
  rule_action = "accept"
  traffic_direction = "egress"
}

resource "aws_ec2_traffic_mirror_filter_rule" "zeek_inbound" {
  count = var.config.zeek_sensor == "1" ? 1 : 0
  description = "Zeek Inbound Rule"
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.zeek_filter[0].id
  destination_cidr_block = "0.0.0.0/0"
  source_cidr_block = "0.0.0.0/0"
  rule_number = 1
  rule_action = "accept"
  traffic_direction = "ingress"
}

resource "aws_ec2_traffic_mirror_session" "zeek_windows_dc_session" {
  count         = var.config.windows_domain_controller_zeek_capture == "1" && var.config.zeek_sensor == "1" ? 1 : 0
  description              = "Zeek Mirror Session for Windows Domain Controller"
  depends_on = [var.windows_domain_controller_instance]
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.zeek_filter[0].id
  traffic_mirror_target_id = aws_ec2_traffic_mirror_target.zeek_target[0].id
  network_interface_id     = var.windows_domain_controller_instance[0].primary_network_interface_id
  session_number           = 100
}

resource "aws_ec2_traffic_mirror_session" "zeek_windows_server_session" {
  count         = var.config.windows_server_zeek_capture == "1" && var.config.zeek_sensor == "1" ? 1 : 0
  description              = "Zeek Mirror Session for Windows Server"
  depends_on = [var.windows_server_instance]
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.zeek_filter[0].id
  traffic_mirror_target_id = aws_ec2_traffic_mirror_target.zeek_target[0].id
  network_interface_id     = var.windows_server_instance[0].primary_network_interface_id
  session_number           = 200
}
