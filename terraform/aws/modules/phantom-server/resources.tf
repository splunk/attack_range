
data "aws_ami" "latest-centos" {
  count       = var.phantom_server.phantom_server == "1" ? 1 : 0
  most_recent = true
  owners      = ["679593333241"] # owned by AWS Marketplace

  filter {
    name   = "name"
    values = ["CentOS-7-2111-20220330_2.x86_64*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# install Phantom on a bare CentOS 7 instance
resource "aws_instance" "phantom-server" {
  count                  = var.phantom_server.phantom_server == "1" ? 1 : 0
  ami                    = data.aws_ami.latest-centos[count.index].id
  instance_type          = "t3.xlarge"
  key_name               = var.general.key_name
  subnet_id              = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip             = "10.0.1.13"
  root_block_device {
    volume_type           = "gp2"
    volume_size           = "30"
    delete_on_termination = "true"
  }
  tags = {
    Name = "ar-phantom-${var.general.key_name}"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "centos"
      host        = aws_instance.phantom-server[0].public_ip
      private_key = file(var.aws.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u centos --private-key ${var.aws.private_key_path} -i '${aws_instance.phantom-server[0].public_ip},' phantom_server.yml -e '${join(" ", [for key, value in var.general : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.phantom_server : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.aws : "${key}=\"${value}\""])}'"
  }
}

resource "aws_eip" "phantom_ip" {
  count    = var.phantom_server.phantom_server == "1" ? 1 : 0
  instance = aws_instance.phantom-server[0].id
}