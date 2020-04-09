
data "aws_ami" "latest-kali-linux" {
  count = var.kali_machine == "1" && var.use_packer_amis=="0" ? 1 : 0
  most_recent = true
  owners = ["679593333241"] # owned by AWS marketplace

  filter {
      name   = "name"
      values = ["Kali Linux 2019.*"]
  }

  filter {
      name   = "virtualization-type"
      values = ["hvm"]
  }
}

resource "aws_instance" "kali_machine" {
  count = var.kali_machine == "1" && var.use_packer_amis=="0" ? 1 : 0
  ami           = data.aws_ami.latest-kali-linux[count.index].id
  instance_type = "t2.medium"
  key_name = var.key_name
  subnet_id = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip = var.kali_machine_private_ip
  tags = {
    Name = "attack-range-kali_machine"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "ec2-user"
      host        = aws_instance.kali_machine[count.index].public_ip
      private_key = file(var.private_key_path)
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ec2-user --private-key ${var.private_key_path} -i '${aws_instance.kali_machine[count.index].public_ip},' playbooks/kali_linux.yml -e 'ansible_python_interpreter=/usr/bin/python3 run_demo=${var.run_demo} demo_scenario=${var.demo_scenario}' "
  }

}

resource "aws_eip" "kali_ip" {
  count = var.kali_machine == "1" && var.use_packer_amis=="0" ? 1 : 0
  instance      = aws_instance.kali_machine[0].id
}



#### Packer ######

data "aws_ami" "kali-machine-packer-ami" {
  count = var.kali_machine == "1" && var.use_packer_amis=="1" ? 1 : 0
  owners       = ["self"]

  filter {
    name   = "name"
    values = [var.kali_machine_packer_ami]
  }

  most_recent = true
}

resource "aws_instance" "kali_machine_packer" {
  count = var.kali_machine == "1" && var.use_packer_amis=="1" ? 1 : 0
  ami           = data.aws_ami.kali-machine-packer-ami[count.index].id
  instance_type = "t2.medium"
  key_name = var.key_name
  subnet_id = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip = var.kali_machine_private_ip
  tags = {
    Name = "attack-range-kali_machine"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "ec2-user"
      host        = aws_instance.kali_machine_packer[count.index].public_ip
      private_key = file(var.private_key_path)
    }
  }

}

resource "aws_eip" "kali_ip_packer" {
  count = var.kali_machine == "1" && var.use_packer_amis=="1" ? 1 : 0
  instance      = aws_instance.kali_machine_packer[0].id
}
