
# standup splunk server
 resource "aws_instance" "splunk-server" {
  ami           = var.splunk_ami
  instance_type = "t2.2xlarge"
  key_name = var.key_name
  subnet_id = var.vpc_subnet1_id
  vpc_security_group_ids = var.vpc_security_group_ids
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
      host        = "${aws_instance.splunk-server.public_ip}"
      private_key = "${file(var.private_key_path)}"
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.private_key_path} -i '${aws_instance.splunk-server.public_ip},' playbooks/splunk_server.yml -e 'ansible_python_interpreter=/usr/bin/python3'"
  }
}

resource "aws_eip" "splunk_ip" {
  instance = aws_instance.splunk-server.id
}


output "splunk_server" {
  value = "http://${aws_eip.splunk_ip.public_ip}:8000"
}

output "splunk_username" {
  value = "admin"
}

output "splunk_password" {
  value = "please use password configured under attack_range.conf -> splunk_admin_password"
}
