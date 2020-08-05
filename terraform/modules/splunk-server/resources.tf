

data "aws_ami" "latest-ubuntu" {
  most_recent = true
  owners = ["099720109477"] # Canonical

  filter {
      name   = "name"
      values = ["ubuntu/images/hvm-ssd/ubuntu-bionic-18.04-amd64-server-*"]
  }

  filter {
      name   = "virtualization-type"
      values = ["hvm"]
  }
}


resource "aws_instance" "splunk-server" {
  ami           = data.aws_ami.latest-ubuntu.id
  instance_type = "t2.2xlarge"
  key_name = var.config.key_name
  subnet_id = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip = var.config.splunk_server_private_ip
  #depends_on = [var.phantom_server_instance]
  root_block_device {
    volume_type = "gp2"
    volume_size = "30"
    delete_on_termination = "true"
  }
  tags = {
    Name = "attack-range-splunk-server"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = aws_instance.splunk-server.public_ip
      private_key = file(var.config.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.config.private_key_path} -i '${aws_instance.splunk-server.public_ip},' playbooks/splunk_server.yml -e 'ansible_python_interpreter=/usr/bin/python3 config=${var.config}'"
  }
}

resource "aws_eip" "splunk_ip" {
  instance = aws_instance.splunk-server.id
}
