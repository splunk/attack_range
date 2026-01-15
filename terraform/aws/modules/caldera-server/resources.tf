
data "aws_ami" "caldera_server" {
  count       = var.caldera_server.caldera_server == "1" ? 1 : 0
  most_recent = true
  owners      = ["679593333241"] # owned by AWS marketplace

  filter {
      name   = "name"
      values = ["debian-12-amd64-2024*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "caldera_server" {
  count                  = var.caldera_server.caldera_server == "1" ? 1 : 0
  ami                    = data.aws_ami.caldera_server[0].id
  instance_type          = "m5.2xlarge"
  key_name               = var.general.key_name
  subnet_id              = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip             = var.caldera_server.private_ip
  associate_public_ip_address = true

  root_block_device {
    volume_type = "gp3"
    volume_size = "60"
    delete_on_termination = "true"
    encrypted  = "true"
  }

  tags = {
    Name = "ar-caldera-${var.general.key_name}-${var.general.attack_range_name}"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "admin"
      host        = self.public_ip
      private_key = file(var.aws.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = <<-EOT
      cat <<EOF > vars/caldera_vars.json
      {
        "ansible_python_interpreter": "/usr/bin/python3",
        "general": ${jsonencode(var.general)},
        "aws": ${jsonencode(var.aws)},
        "caldera_server": ${jsonencode(var.caldera_server)},
        "public_ip": ${jsonencode(self.public_ip)},
        "aws_eip": ${jsonencode(var.aws.use_elastic_ips)}
      }
      EOF
    EOT
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = <<-EOT
      ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u admin --private-key '${var.aws.private_key_path}' -i '${self.public_ip},' caldera_server.yml -e "@vars/caldera_vars.json"
    EOT
  }

}

