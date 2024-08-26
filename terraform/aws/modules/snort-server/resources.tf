

data "aws_ami" "snort_server" {
  count       = (var.snort_server.snort_server == "1")  ? 1 : 0
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "snort_sensor" {
  count       = var.snort_server.snort_server == "1" ? 1 : 0
  ami           = data.aws_ami.snort_server[0].id
  instance_type = "m5.2xlarge"
  key_name      = var.general.key_name
  subnet_id = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip = "10.0.1.60"
  associate_public_ip_address = true

  tags = {
    Name = "ar-snort-${var.general.key_name}-${var.general.attack_range_name}"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = self.public_ip
      private_key = file(var.aws.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = <<-EOT
      cat <<EOF > vars/snort_vars.json
      {
        "ansible_python_interpreter": "/usr/bin/python3",
        "general": ${jsonencode(var.general)},
        "splunk_server": ${jsonencode(var.splunk_server)},
        "snort_server": ${jsonencode(var.snort_server)},
      }
      EOF
    EOT
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key '${var.aws.private_key_path}' -i '${self.public_ip},' snort_server.yml -e @vars/snort_vars.json"
  }
}

resource "aws_eip" "snort_ip" {
  count       = (var.snort_server.snort_server == "1") && (var.aws.use_elastic_ips == "1") ? 1 : 0
  instance    = aws_instance.snort_sensor[0].id
}

resource "aws_ec2_traffic_mirror_target" "snort_target" {
  count = var.snort_server.snort_server == "1" ? 1 : 0
  description          = "VPC Tap for Snort"
  network_interface_id = aws_instance.snort_sensor[0].primary_network_interface_id
}

resource "aws_ec2_traffic_mirror_filter" "snort_filter" {
  count = var.snort_server.snort_server == "1" ? 1 : 0
  description = "Snort Mirror Filter - Allow All"
}

resource "aws_ec2_traffic_mirror_filter_rule" "snort_outbound" {
  count = var.snort_server.snort_server == "1" ? 1 : 0
  description = "Snort Outbound Rule"
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.snort_filter[0].id
  destination_cidr_block = "0.0.0.0/0"
  source_cidr_block = "0.0.0.0/0"
  rule_number = 1
  rule_action = "accept"
  traffic_direction = "egress"
}

resource "aws_ec2_traffic_mirror_filter_rule" "snort_inbound" {
  count = var.snort_server.snort_server == "1" ? 1 : 0
  description = "Snort Inbound Rule"
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.snort_filter[0].id
  destination_cidr_block = "0.0.0.0/0"
  source_cidr_block = "0.0.0.0/0"
  rule_number = 1
  rule_action = "accept"
  traffic_direction = "ingress"
}

resource "aws_ec2_traffic_mirror_session" "snort_windows_session" {
  count                    = var.snort_server.snort_server == "1" ? length(var.windows_servers) : 0
  description              = "Snort Mirror Session for Windows Server"
  depends_on               = [var.windows_server_instances]
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.snort_filter[0].id
  traffic_mirror_target_id = aws_ec2_traffic_mirror_target.snort_target[0].id
  network_interface_id     = var.windows_server_instances[count.index].primary_network_interface_id
  session_number           = 100
}

resource "aws_ec2_traffic_mirror_session" "snort_linux_session" {
  count                    = var.snort_server.snort_server == "1" ? length(var.linux_servers) : 0
  description              = "Snort Mirror Session for Linux Server"
  depends_on               = [var.linux_server_instances]
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.snort_filter[0].id
  traffic_mirror_target_id = aws_ec2_traffic_mirror_target.snort_target[0].id
  network_interface_id     = var.linux_server_instances[count.index].primary_network_interface_id
  session_number           = 100
}