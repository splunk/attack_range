# install phantom on a fresh centos 7 aws instance

data "aws_ami" "latest-centos" {
  count       = var.config.phantom_server == "1" ? 1 : 0
  most_recent = true
  owners      = ["679593333241"] # owned by AWS Marketplace

  filter {
    name   = "name"
    values = ["CentOS Linux 7 x86_64 HVM EBS ENA 1901_01-b7ee8a69-ee97-4a49-9e68-afaee216db2e-ami-05713873c6794f575.4"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# install Phantom on a bare CentOS 7 instance
resource "aws_instance" "phantom-server" {
  count                  = var.config.phantom_server == "1" ? 1 : 0
  ami                    = data.aws_ami.latest-centos[count.index].id
  instance_type          = var.config.instance_type_ec2
  key_name               = var.config.key_name
  subnet_id              = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip             = var.config.phantom_server_private_ip
  root_block_device {
    volume_type           = "gp2"
    volume_size           = "30"
    delete_on_termination = "true"
  }
  tags = {
    Name = "ar-phantom-${var.config.range_name}-${var.config.key_name}"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "centos"
      host        = aws_instance.phantom-server[0].public_ip
      private_key = file(var.config.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../../ansible/"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u centos --private-key ${var.config.private_key_path} -i '${aws_instance.phantom-server[0].public_ip},' playbooks/phantom_server.yml -e 'phantom_admin_password=${var.config.attack_range_password} phantom_community_username=${var.config.phantom_community_username} phantom_community_password=${var.config.phantom_community_password} phantom_server_private_ip=${var.config.phantom_server_private_ip}'"
  }
}

resource "aws_eip" "phantom_ip" {
  count    = var.config.phantom_server == "1" ? 1 : 0
  instance = aws_instance.phantom-server[0].id
}
