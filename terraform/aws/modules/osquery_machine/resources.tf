data "aws_ami" "latest-ubuntu" {
  count       = var.config.osquery_machine == "1" ? 1 : 0
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "osquery_machine" {
  count                  = var.config.osquery_machine == "1" ? 1 : 0  
  ami                    = data.aws_ami.latest-ubuntu[count.index].id
  instance_type          = var.config.instance_type_ec2
  key_name               = var.config.key_name
  subnet_id              = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip             = var.config.osquery_linux_private_ip
  tags = {
    Name = "ar-osquerylnx-${var.config.range_name}-${var.config.key_name}"
  }


  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = aws_instance.osquery_machine[count.index].public_ip
      private_key = file(var.config.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../../ansible/"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.config.private_key_path} -i '${aws_instance.osquery_machine[count.index].public_ip},' playbooks/osquery_machine.yml -e 'splunk_indexer_ip=${var.config.splunk_server_private_ip} splunk_uf_url=${var.config.splunk_uf_linux_deb_url} custom_osquery_conf=${var.config.osquery_custom_config_file}'"
  
  }
}


resource "aws_eip" "osquery_ip" {
  count    = var.config.osquery_machine == "1" ? 1 : 0
  instance = aws_instance.osquery_machine[0].id
}