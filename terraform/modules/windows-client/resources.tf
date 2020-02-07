
data "aws_ami" "windows-client-ami" {
  count = var.windows_client == "1" && var.use_packer_amis=="0" ? 1 : 0
  owners       = ["self"]

  filter {
    name   = "name"
    values = [var.windows_client_os]
  }

  most_recent = true
}


resource "aws_instance" "windows_client" {
  count         = var.windows_client == "1" && var.use_packer_amis=="0" ? 1 : 0
  ami           = "${data.aws_ami.windows-client-ami[count.index].id}"
  instance_type = "t2.2xlarge"
  key_name = var.key_name
  subnet_id = "${var.vpc_subnet_id}"
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip = var.windows_client_private_ip
  depends_on = [var.windows_domain_controller_instance]
  tags = {
    Name = "attack-range-windows-client"
  }

  provisioner "remote-exec" {
    inline = [
      "net user ${var.win_username} /active:yes",
      "net user ${var.win_username} ${var.win_password}"
      ]

    connection {
      type     = "winrm"
      user     = "admin"
      password = "admin"
      host     = "${aws_instance.windows_client[count.index].public_ip}"
      port     = 5985
      insecure = true
      https    = false
      timeout  = "7m"
    }
  }

  provisioner "remote-exec" {
    inline = [
      "net user admin /active:no"
      ]

    connection {
      type     = "winrm"
      user     = "${var.win_username}"
      password = "${var.win_password}"
      host     = "${aws_instance.windows_client[count.index].public_ip}"
      port     = 5985
      insecure = true
      https    = false
      timeout  = "7m"
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ansible-playbook -i '${aws_instance.windows_client[count.index].public_ip},' playbooks/windows_workstation.yml --extra-vars 'splunk_indexer_ip=${var.splunk_server_private_ip} ansible_user=${var.win_username} ansible_password=${var.win_password} win_password=${var.win_password} splunk_uf_win_url=${var.splunk_uf_win_url} win_sysmon_url=${var.win_sysmon_url} win_sysmon_template=${var.win_sysmon_template} splunk_admin_password=${var.splunk_admin_password} windows_domain_controller_private_ip=${var.windows_domain_controller_private_ip} windows_server_join_domain=${var.windows_client_join_domain}'"
  }

}

resource "aws_eip" "windows_client_ip" {
  count         = var.windows_client == "1" && var.use_packer_amis=="0" ? 1 : 0
  instance = aws_instance.windows_client[0].id
}


##### packer #######

data "aws_ami" "windows-client-packer-ami" {
  count = var.windows_client == "1" && var.use_packer_amis=="1" ? 1 : 0
  owners       = ["self"]

  filter {
    name   = "name"
    values = [var.windows_client_packer_ami]
  }

  most_recent = true
}


resource "aws_instance" "windows_client_packer" {
  count         = var.windows_client == "1" && var.use_packer_amis=="1" ? 1 : 0
  ami           = "${data.aws_ami.windows-client-packer-ami[count.index].id}"
  instance_type = "t2.2xlarge"
  key_name = var.key_name
  subnet_id = "${var.vpc_subnet_id}"
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip = var.windows_client_private_ip
  depends_on = [var.windows_domain_controller_instance]
  tags = {
    Name = "attack-range-windows-client"
  }

  provisioner "remote-exec" {
    inline = [
      "net user ${var.win_username} /active:yes",
      "net user ${var.win_username} ${var.win_password}"
      ]

    connection {
      type     = "winrm"
      user     = "admin"
      password = "admin"
      host     = "${aws_instance.windows_client_packer[count.index].public_ip}"
      port     = 5985
      insecure = true
      https    = false
      timeout  = "7m"
    }
  }

  provisioner "remote-exec" {
    inline = [
      "net user admin /active:no"
      ]

    connection {
      type     = "winrm"
      user     = "${var.win_username}"
      password = "${var.win_password}"
      host     = "${aws_instance.windows_client_packer[count.index].public_ip}"
      port     = 5985
      insecure = true
      https    = false
      timeout  = "7m"
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ansible-playbook -i '${aws_instance.windows_client_packer[count.index].public_ip},' playbooks/windows_workstation_packer_terraform.yml --extra-vars 'splunk_indexer_ip=${var.splunk_server_private_ip} ansible_user=${var.win_username} ansible_password=${var.win_password} win_password=${var.win_password} splunk_uf_win_url=${var.splunk_uf_win_url} win_sysmon_url=${var.win_sysmon_url} win_sysmon_template=${var.win_sysmon_template} splunk_admin_password=${var.splunk_admin_password} windows_domain_controller_private_ip=${var.windows_domain_controller_private_ip} windows_server_join_domain=${var.windows_client_join_domain}'"
  }

}

resource "aws_eip" "windows_client_ip_packer" {
  count         = var.windows_client == "1" && var.use_packer_amis=="1" ? 1 : 0
  instance = aws_instance.windows_client_packer[0].id
}
