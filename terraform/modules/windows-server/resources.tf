
data "aws_ami" "latest-windows-server-2016" {
  count = var.windows_server == "1" && var.use_packer_amis=="0" ? 1 : 0
  most_recent = true
  owners = ["801119661308"] # Canonical

  filter {
      name   = "name"
      values = [var.windows_server_os]
  }

  filter {
      name   = "virtualization-type"
      values = ["hvm"]
  }
}


resource "aws_instance" "windows_server" {
  count         = var.windows_server == "1" && var.use_packer_amis=="0" ? 1 : 0
  ami           = "${data.aws_ami.latest-windows-server-2016[count.index].id}"
  instance_type = "t2.2xlarge"
  key_name = var.key_name
  subnet_id = "${var.vpc_subnet_id}"
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip = var.windows_server_private_ip
  depends_on = [var.windows_domain_controller_instance]
  tags = {
    Name = "attack-range-windows-server"
  }
  user_data = <<EOF
<powershell>
$admin = [adsi]("WinNT://./${var.win_username}, user")
$admin.PSBase.Invoke("SetPassword", "${var.win_password}")
Invoke-Expression ((New-Object System.Net.Webclient).DownloadString('https://raw.githubusercontent.com/ansible/ansible/devel/examples/scripts/ConfigureRemotingForAnsible.ps1'))
</powershell>
EOF

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type     = "winrm"
      user     = "${var.win_username}"
      password = "${var.win_password}"
      host     = "${aws_instance.windows_server[count.index].public_ip}"
      port     = 5986
      insecure = true
      https    = true
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ansible-playbook -i '${aws_instance.windows_server[count.index].public_ip},' playbooks/windows_dc_client.yml --extra-vars 'splunk_indexer_ip=${var.splunk_server_private_ip} ansible_user=${var.win_username} ansible_password=${var.win_password} win_password=${var.win_password} splunk_uf_win_url=${var.splunk_uf_win_url} win_sysmon_url=${var.win_sysmon_url} win_sysmon_template=${var.win_sysmon_template} splunk_admin_password=${var.splunk_admin_password} windows_domain_controller_private_ip=${var.windows_domain_controller_private_ip} windows_server_join_domain=${var.windows_server_join_domain}'"
  }

}

resource "aws_eip" "windows_server_ip_client" {
  count         = var.windows_server == "1" && var.use_packer_amis=="0" ? 1 : 0
  instance = aws_instance.windows_server[0].id
}


###### Packer #########

data "aws_ami" "windows-server-packer-ami" {
  count = var.windows_server == "1" && var.use_packer_amis=="1" ? 1 : 0
  owners       = ["self"]

  filter {
    name   = "name"
    values = [var.windows_server_packer_ami]
  }

  most_recent = true
}


resource "aws_instance" "windows_server_packer" {
  count         = var.windows_server == "1" && var.use_packer_amis=="1" ? 1 : 0
  ami           = "${data.aws_ami.windows-server-packer-ami[count.index].id}"
  instance_type = "t2.2xlarge"
  key_name = var.key_name
  subnet_id = "${var.vpc_subnet_id}"
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip = var.windows_server_private_ip
  depends_on = [var.windows_domain_controller_instance_packer]
  tags = {
    Name = "attack-range-windows-server"
  }
  user_data = <<EOF
<powershell>
$admin = [adsi]("WinNT://./${var.win_username}, user")
$admin.PSBase.Invoke("SetPassword", "${var.win_password}")
Invoke-Expression ((New-Object System.Net.Webclient).DownloadString('https://raw.githubusercontent.com/ansible/ansible/devel/examples/scripts/ConfigureRemotingForAnsible.ps1'))
</powershell>
EOF

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type     = "winrm"
      user     = "${var.win_username}"
      password = "${var.win_password}"
      host     = "${aws_instance.windows_server_packer[count.index].public_ip}"
      port     = 5986
      insecure = true
      https    = true
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ansible-playbook -i '${aws_instance.windows_server_packer[count.index].public_ip},' playbooks/windows_dc_client_packer_terraform.yml --extra-vars 'splunk_indexer_ip=${var.splunk_server_private_ip} ansible_user=${var.win_username} ansible_password=${var.win_password} win_password=${var.win_password} splunk_uf_win_url=${var.splunk_uf_win_url} win_sysmon_url=${var.win_sysmon_url} win_sysmon_template=${var.win_sysmon_template} splunk_admin_password=${var.splunk_admin_password} windows_domain_controller_private_ip=${var.windows_domain_controller_private_ip} windows_server_join_domain=${var.windows_server_join_domain}'"
  }

}

resource "aws_eip" "windows_server_ip_client_packer" {
  count         = var.windows_server == "1" && var.use_packer_amis=="1" ? 1 : 0
  instance = aws_instance.windows_server_packer[0].id
}
