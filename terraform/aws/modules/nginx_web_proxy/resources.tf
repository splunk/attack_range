data "aws_ami" "latest-nginx-plus" {
count = var.config.nginx_web_proxy == "1" ? 1 : 0
  most_recent = true
  owners      = ["679593333241"] # Nginx

  filter {
    name   = "name"
    values = ["nginx-plus-app-protect-ubuntu-18.04-v2.4-x86_64-developer*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "nginx_web_proxy" {
  count                  = var.config.nginx_web_proxy == "1" ? 1 : 0
  ami                    = data.aws_ami.latest-nginx-plus[count.index].id
  instance_type          = "t3.small"
  key_name               = var.config.key_name
  subnet_id              = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip             = var.config.nginx_web_proxy_private_ip
  root_block_device {
    volume_type           = "gp2"
    volume_size           = "30"
    delete_on_termination = "true"
  }
  tags = {
    Name = "ar-nginx_web_proxy-${var.config.range_name}-${var.config.key_name}"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = aws_instance.nginx_web_proxy[0].public_ip
      private_key = file(var.config.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../../../ansible/"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.config.private_key_path} -i '${aws_instance.nginx_web_proxy[0].public_ip},' playbooks/nginx_web_proxy.yml -e ' nginx_web_proxy_private_ip=${var.config.nginx_web_proxy_private_ip} splunk_indexer_ip=${var.config.splunk_server_private_ip} splunk_uf_url=${var.config.splunk_uf_linux_deb_url} key_name=${var.config.key_name} nginx_web_proxy_host=${var.config.nginx_web_proxy_host} nginx_web_proxy_port=${var.config.nginx_web_proxy_port}'"
  }
}

resource "aws_eip" "nginx_web_proxy_ip" {
  count    = var.config.nginx_web_proxy == "1" && var.config.use_elastic_ips == "1" ? 1 : 0
  instance = aws_instance.nginx_web_proxy[0].id
}
