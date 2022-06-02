
data "aws_ami" "linux_server" {
  count = length(var.linux_servers)
  most_recent = true
  owners      = [var.aws.image_owner] 

  filter {
    name   = "name"
    values = [var.linux_servers[count.index].image_owner]
  }
}

resource "aws_instance" "linux_server" {
  count                  = length(var.linux_servers)
  ami                    = data.aws_ami.linux_server[count.index].id
  instance_type          = "t3.xlarge"
  key_name               = var.general.key_name
  subnet_id              = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip             = "10.0.1.${21 + count.index}"

  root_block_device {
    volume_type = "gp2"
    volume_size = "60"
    delete_on_termination = "true"
  }

  tags = {
    Name = "ar-linux-${var.general.key_name}-${count.index}"
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
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.aws.private_key_path} -i '${self.public_ip},' linux_server_post.yml -e 'ansible_python_interpreter=/usr/bin/python3 ${join(" ", [for key, value in var.general : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.linux_servers[count.index] : "${key}=\"${value}\""])} '"
  }

}

resource "aws_eip" "linux_server_ip" {
  count = length(var.linux_servers)
  instance = aws_instance.linux_server[count.index].id
}