

data "aws_ami" "splunk_server" {
  most_recent = true
  owners      = ["591511147606"] 

  filter {
    name   = "name"
    values = [var.splunk_server.image]
  }
}

resource "aws_instance" "splunk-server" {
  ami                    = data.aws_ami.splunk_server.id
  instance_type          = "t3.2xlarge"
  key_name               = var.general.key_name
  subnet_id              = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip             = "10.0.1.12"

  root_block_device {
    volume_type = "gp2"
    volume_size = "60"
    delete_on_termination = "true"
  }

  tags = {
    Name = "ar-splunk-${var.general.key_name}"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = aws_instance.splunk-server.public_ip
      private_key = file(var.aws.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.aws.private_key_path} -i '${aws_instance.splunk-server.public_ip},' splunk_server_post.yml -e 'ansible_python_interpreter=/usr/bin/python3 ${join(" ", [for key, value in var.general : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.aws : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.splunk_server : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.phantom_server : "${key}=\"${value}\""])}'"
  }

}

resource "aws_eip" "splunk_ip" {
  instance = aws_instance.splunk-server.id
}
