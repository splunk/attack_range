# install phantom on a fresh centos 7 aws instance

data "aws_ami" "latest-centos" {
most_recent = true
owners = ["679593333241"] # owned by AWS Marketplace

  filter {
      name   = "name"
      values = ["CentOS Linux 7 x86_64 HVM EBS ENA 1901*"]
  }

  filter {
      name   = "virtualization-type"
      values = ["hvm"]
  }
}

# install Phantom on a bare CentOS 7 instance
resource "aws_instance" "phantom-server" {
  count         = var.phantom_server ? 1 : 0
  ami           = "${data.aws_ami.latest-centos.id}"
  instance_type = "t3a.xlarge"
  key_name = var.key_name
  subnet_id = var.vpc_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip = var.phantom_server_private_ip
  root_block_device {
    volume_type = "gp2"
    volume_size = "30"
    delete_on_termination = "true"
  }
  tags = {
    Name = "attack-range-phantom-server"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "centos"
      host        = "${aws_instance.phantom-server[0].public_ip}"
      private_key = "${file(var.private_key_path)}"
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible/"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u centos --private-key ${var.private_key_path} -i '${aws_instance.phantom-server[0].public_ip},' playbooks/phantom_server.yml -e 'phantom_admin_password=${var.phantom_admin_password} phantom_community_username=${var.phantom_community_username} phantom_community_password=${var.phantom_community_password} phantom_server_private_ip=${var.phantom_server_private_ip}'"
  }
}

resource "aws_eip" "phantom_ip" {
  count    = var.phantom_server ? 1 : 0
  instance = aws_instance.phantom-server[0].id
}


output "phantom_server_base_url" {
  value = "https://${aws_eip.phantom_ip[0].public_ip}"
}

output "phantom_username" {
  value = "admin"
}

output "phantom_password" {
  value = "please use password configured under attack_range.conf -> phantom_admin_password"
}

output "phantom_ssh_command" {
  value = "ssh -i ${var.private_key_path} centos@${aws_eip.phantom_ip[0].public_ip}"
}
