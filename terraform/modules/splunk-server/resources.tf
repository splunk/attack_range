

data "aws_ami" "latest-ubuntu" {
  count = var.use_packer_amis ? 0 : 1
  most_recent = true
  owners = ["679593333241"] # Canonical

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
  count = var.use_packer_amis ? 0 : 1
  ami           = "${data.aws_ami.latest-ubuntu[count.index].id}"
  instance_type = "t2.2xlarge"
  key_name = var.key_name
  subnet_id = var.vpc_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip = var.splunk_server_private_ip
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
      host        = "${aws_instance.splunk-server[count.index].public_ip}"
      private_key = "${file(var.private_key_path)}"
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ubuntu --private-key ${var.private_key_path} -i '${aws_instance.splunk-server[count.index].public_ip},' playbooks/splunk_server.yml -e 'ansible_python_interpreter=/usr/bin/python3 splunk_admin_password=${var.splunk_admin_password} splunk_url=${var.splunk_url} splunk_binary=${var.splunk_binary} s3_bucket_url=${var.s3_bucket_url} splunk_escu_app=${var.splunk_escu_app} splunk_asx_app=${var.splunk_asx_app} splunk_windows_ta=${var.splunk_windows_ta} splunk_cim_app=${var.splunk_cim_app} splunk_sysmon_ta=${var.splunk_sysmon_ta} splunk_python_app=${var.splunk_python_app} splunk_mltk_app=${var.splunk_mltk_app} caldera_password=${var.caldera_password}'"
  }
}

resource "aws_eip" "splunk_ip" {
  count = var.use_packer_amis ? 0 : 1
  instance = aws_instance.splunk-server[count.index].id
}


#### packer ####

data "aws_ami" "splunk-ami-packer" {
  count = var.use_packer_amis ? 1 : 0
  owners       = ["self"]

  filter {
    name   = "name"
    values = [var.splunk_packer_ami]
  }

  most_recent = true
}


resource "aws_instance" "splunk-server-packer" {
  count = var.use_packer_amis ? 1 : 0
  ami           = "${data.aws_ami.splunk-ami-packer[count.index].id}"
  instance_type = "t2.2xlarge"
  key_name = var.key_name
  subnet_id = var.vpc_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip = var.splunk_server_private_ip
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
      host        = "${aws_instance.splunk-server-packer[count.index].public_ip}"
      private_key = "${file(var.private_key_path)}"
    }
  }
}

resource "aws_eip" "splunk_ip_packer" {
  count = var.use_packer_amis ? 1 : 0
  instance = aws_instance.splunk-server-packer[count.index].id
}
