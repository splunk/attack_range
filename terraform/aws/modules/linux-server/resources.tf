

data "aws_ami" "linux_server" {
  count = length(var.linux_servers)
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

resource "aws_instance" "linux_server" {
  count                  = length(var.linux_servers)
  ami                    = data.aws_ami.linux_server[count.index].id
  instance_type          = (var.zeek_server.zeek_server == "1" || var.snort_server.snort_server == "1") ? "m5.2xlarge" : "t3.xlarge"
  key_name               = var.general.key_name
  subnet_id              = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip             = "10.0.1.${21 + count.index}"
  associate_public_ip_address = true

  root_block_device {
    volume_type = "gp2"
    volume_size = "60"
    delete_on_termination = "true"
  }

  tags = {
    Name = "ar-linux-${var.general.key_name}-${var.general.attack_range_name}-${count.index}"
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
      cat <<EOF > vars/linux_vars_${count.index}.json
      {
        "ansible_python_interpreter": "/usr/bin/python3",
        "general": ${jsonencode(var.general)},
        "splunk_server": ${jsonencode(var.splunk_server)},
        "linux_servers": ${jsonencode(var.linux_servers[count.index])},
        "simulation": ${jsonencode(var.simulation)},
      }
      EOF
    EOT
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key '${var.aws.private_key_path}' -i '${self.public_ip},' linux_server.yml -e @vars/linux_vars_${count.index}.json"
  }

}

resource "aws_eip" "linux_server_ip" {
  count = (var.aws.use_elastic_ips == "1") ? length(var.linux_servers) : 0
  instance = aws_instance.linux_server[count.index].id
}
