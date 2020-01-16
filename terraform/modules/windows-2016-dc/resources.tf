
data "aws_ami" "latest-windows-server-2016" {
most_recent = true
owners = ["801119661308"] # Canonical

  filter {
      name   = "name"
      values = ["Windows_Server-2016-English-Full-Base-2019.12.16"]
  }

  filter {
      name   = "virtualization-type"
      values = ["hvm"]
  }
}

# resource "aws_ebs_volume" "win2016_volume" {
#   count         = var.windows_2016_dc ? 1 : 0
#   availability_zone = var.availability_zone
#   size              = 50
# }


# standup windows 2016 domain controller
resource "aws_instance" "windows_2016_dc" {
  count         = var.windows_2016_dc ? 1 : 0
  ami           = "${data.aws_ami.latest-windows-server-2016.id}"
  instance_type = "t2.2xlarge"
  key_name = var.key_name
  subnet_id = "${var.vpc_subnet_id}"
  private_ip = var.windows_2016_dc_private_ip
  vpc_security_group_ids = [var.vpc_security_group_ids]
  tags = {
    Name = "attack-range-windows-2016-dc"
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
      host     = "${aws_instance.windows_2016_dc[count.index].public_ip}"
      port     = 5986
      insecure = true
      https    = true
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ansible-playbook -i '${aws_instance.windows_2016_dc[count.index].public_ip},' playbooks/windows_dc.yml --extra-vars 'splunk_indexer_ip=${var.splunk_server_private_ip} ansible_user=${var.win_username} ansible_password=${var.win_password} win_password=${var.win_password} splunk_uf_win_url=${var.splunk_uf_win_url} win_sysmon_url=${var.win_sysmon_url} win_sysmon_template=${var.win_sysmon_template} splunk_admin_password=${var.splunk_admin_password}'"
  }

}

resource "aws_eip" "windows_server_ip" {
  count         = var.windows_2016_dc ? 1 : 0
  instance = aws_instance.windows_2016_dc[0].id
}

output "windows_dc_ip" {
  value = "connect using an RDP client to ${ join(" ", aws_eip.windows_server_ip.*.public_ip) } on 3389"
}

output "windows_password" {
  value = "please use password configured under attack_range.conf -> win_password"
}
