
data "aws_ami" "latest-windows-server-2016" {
  count = var.windows_domain_controller == "1" && var.use_packer_amis=="0" ? 1 : 0
  most_recent = true
  owners = ["801119661308"] # Canonical

  filter {
      name   = "name"
      values = [var.windows_domain_controller_os]
  }

  filter {
      name   = "virtualization-type"
      values = ["hvm"]
  }
}


resource "aws_instance" "windows_domain_controller" {
  count         = var.windows_domain_controller == "1" && var.use_packer_amis=="0" ? 1 : 0
  ami           = "${data.aws_ami.latest-windows-server-2016[count.index].id}"
  instance_type = "t2.2xlarge"
  key_name = var.key_name
  subnet_id = "${var.vpc_subnet_id}"
  private_ip = var.windows_domain_controller_private_ip
  vpc_security_group_ids = [var.vpc_security_group_ids]
  tags = {
    Name = "attack-range-windows-domain-controller"
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
      host     = "${aws_instance.windows_domain_controller[count.index].public_ip}"
      port     = 5986
      insecure = true
      https    = true
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ansible-playbook -i '${aws_instance.windows_domain_controller[count.index].public_ip},' playbooks/windows_dc.yml --extra-vars 'splunk_indexer_ip=${var.splunk_server_private_ip} ansible_user=${var.win_username} ansible_password=${var.win_password} win_password=${var.win_password} splunk_uf_win_url=${var.splunk_uf_win_url} win_sysmon_url=${var.win_sysmon_url} win_sysmon_template=${var.win_sysmon_template} splunk_admin_password=${var.splunk_admin_password}'"
  }

}

resource "aws_eip" "windows_server_ip" {
  count         = var.windows_domain_controller == "1" && var.use_packer_amis=="0" ? 1 : 0
  instance = aws_instance.windows_domain_controller[0].id
}


#### packer ####

data "aws_ami" "windows-domain-controller-packer-ami" {
  count = var.windows_domain_controller == "1" && var.use_packer_amis=="1" ? 1 : 0
  owners       = ["self"]

  filter {
    name   = "name"
    values = [var.windows_domain_controller_packer_ami]
  }

  most_recent = true
}


resource "aws_instance" "windows_domain_controller_packer" {
  count         = var.windows_domain_controller == "1" && var.use_packer_amis=="1" ? 1 : 0
  ami           = "${data.aws_ami.windows-domain-controller-packer-ami[count.index].id}"
  instance_type = "t2.2xlarge"
  key_name = var.key_name
  subnet_id = "${var.vpc_subnet_id}"
  private_ip = var.windows_domain_controller_private_ip
  vpc_security_group_ids = [var.vpc_security_group_ids]
  tags = {
    Name = "attack-range-windows-domain-controller"
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
      host     = "${aws_instance.windows_domain_controller_packer[count.index].public_ip}"
      port     = 5986
      insecure = true
      https    = true
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ansible-playbook -i '${aws_instance.windows_domain_controller_packer[count.index].public_ip},' playbooks/windows_dc_packer2.yml --extra-vars 'splunk_indexer_ip=${var.splunk_server_private_ip} ansible_user=${var.win_username} ansible_password=${var.win_password} win_password=${var.win_password} splunk_uf_win_url=${var.splunk_uf_win_url} win_sysmon_url=${var.win_sysmon_url} win_sysmon_template=${var.win_sysmon_template} splunk_admin_password=${var.splunk_admin_password}'"
  }

}

resource "aws_eip" "windows_server_ip_packer" {
  count         = var.windows_domain_controller == "1" && var.use_packer_amis=="1" ? 1 : 0
  instance = aws_instance.windows_domain_controller_packer[0].id
}
