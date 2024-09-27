

data "aws_ami" "latest-centos" {
  count       = (var.phantom_server.phantom_server == "1") ? 1 : 0
  most_recent = true
  owners      = ["309956199498"] 

  filter {
    name   = "name"
    values = ["RHEL-8.9.0_HVM-20240327-x86_64-4-Hourly2-GP3"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# install Phantom on a bare CentOS 7 instance
resource "aws_instance" "phantom-server" {
  count                  = var.phantom_server.phantom_server == "1" ? 1 : 0
  ami                    = data.aws_ami.latest-centos[0].id
  instance_type          = "t3.xlarge"
  key_name               = var.general.key_name
  subnet_id              = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip             = "10.0.1.13"
  associate_public_ip_address = true
  root_block_device {
    volume_type           = "gp2"
    volume_size           = "30"
    delete_on_termination = "true"
  }
  tags = {
    Name = "ar-phantom-${var.general.key_name}-${var.general.attack_range_name}"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "ec2-user"
      host        = self.public_ip
      private_key = file(var.aws.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = <<-EOT
      cat <<EOF > vars/phantom_vars.json
      {
        "general": ${jsonencode(var.general)},
        "aws": ${jsonencode(var.aws)},
        "phantom_server": ${jsonencode(var.phantom_server)},
      }
      EOF
    EOT
  }


  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ec2-user --private-key '${var.aws.private_key_path}' -i '${self.public_ip},' phantom_server.yml -e @vars/phantom_vars.json"
  }
}

resource "aws_eip" "phantom_ip" {
  count    = (var.phantom_server.phantom_server == "1") && (var.aws.use_elastic_ips == "1") ? 1 : 0
  instance = aws_instance.phantom-server[0].id
}
