

data "aws_ami" "nginx_server_packer" {
  count = (var.nginx_server.nginx_server == "1") && (var.general.use_prebuilt_images_with_packer == "1") ? 1 : 0
  most_recent = true
  owners      = ["self"] 

  filter {
    name   = "name"
    values = [var.nginx_server.nginx_image]
  }
}

data "aws_ami" "nginx_server" {
  count = (var.nginx_server.nginx_server == "1") && (var.general.use_prebuilt_images_with_packer == "0") ? 1 : 0
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

resource "aws_instance" "nginx_server" {
  count                  = var.nginx_server.nginx_server == "1" ? 1 : 0
  ami                    = var.general.use_prebuilt_images_with_packer == "1" ? data.aws_ami.nginx_server_packer[0].id : data.aws_ami.nginx_server[0].id
  instance_type          = "t3.small"
  key_name               = var.general.key_name
  subnet_id              = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip             = "10.0.1.31"
  associate_public_ip_address = true
  
  root_block_device {
    volume_type = "gp2"
    volume_size = "20"
    delete_on_termination = "true"
  }

  tags = {
    Name = "ar-nginx-${var.general.key_name}-${var.general.attack_range_name}"
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
    working_dir = "../../packer/ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.aws.private_key_path} -i '${self.public_ip},' nginx_web_proxy.yml -e 'ansible_python_interpreter=/usr/bin/python3 ${join(" ", [for key, value in var.general : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.nginx_server : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.splunk_server : "${key}=\"${value}\""])}'"
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.aws.private_key_path} -i '${self.public_ip},' nginx_server_post.yml -e 'ansible_python_interpreter=/usr/bin/python3 ${join(" ", [for key, value in var.general : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.nginx_server : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.splunk_server : "${key}=\"${value}\""])}'"
  }

}

resource "aws_eip" "nginx_server_ip" {
  count = (var.nginx_server.nginx_server == "1") && (var.aws.use_elastic_ips == "1") ? 1 : 0
  instance = aws_instance.nginx_server[count.index].id
}