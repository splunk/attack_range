
data "aws_ami" "windows_ami" {
  count = length(var.windows_servers)
  most_recent = true
  owners      = ["self"]

  filter {
    name   = "name"
    values = [var.windows_servers[count.index].image]
  }
}

resource "aws_instance" "windows_server" {
  count = length(var.windows_servers)
  ami = data.aws_ami.windows_ami[count.index].id
  instance_type = "t3.xlarge"
  key_name = var.general.key_name
  subnet_id = var.ec2_subnet_id
  private_ip = "10.0.1.${14 + count.index}"
  vpc_security_group_ids = [var.vpc_security_group_ids]
  tags = {
    Name = "ar-win-${var.general.key_name}-${var.general.attack_range_name}-${count.index}"
  }
  user_data = <<EOF
<powershell>
$admin = [adsi]("WinNT://./Administrator, user")
$admin.PSBase.Invoke("SetPassword", "${var.general.attack_range_password}")
winrm quickconfig -q
winrm set winrm/config/winrs '@{MaxMemoryPerShellMB="1024"}'
winrm set winrm/config '@{MaxTimeoutms="1800000"}'
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
winrm set winrm/config/service/auth '@{Basic="true"}'
netsh advfirewall firewall add rule name="WinRM 5985" protocol=TCP dir=in localport=5985 action=allow
netsh advfirewall firewall add rule name="WinRM 5986" protocol=TCP dir=in localport=5986 action=allow
net stop winrm
sc.exe config winrm start=auto
net start winrm
Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -name "fDenyTSConnections" -value 0
Enable-PSRemoting -SkipNetworkProfileCheck -Force
</powershell>
EOF

  provisioner "remote-exec" {
    inline = [
      "echo booted"
      ]

    connection {
      type     = "winrm"
      user     = "Administrator"
      #password = "${rsadecrypt(aws_instance.windows_server[count.index].password_data, file(var.aws.private_key_path))}"
      password = var.general.attack_range_password
      host     = self.public_ip
      port     = 5985
      insecure = true
      https    = false
      timeout  = "10m"
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ansible-playbook -i '${self.public_ip},' windows_post.yml --extra-vars 'ansible_user=Administrator ansible_password=${var.general.attack_range_password} ansible_winrm_operation_timeout_sec=120 ansible_winrm_read_timeout_sec=150 attack_range_password=${var.general.attack_range_password} ${join(" ", [for key, value in var.windows_servers[count.index] : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.simulation : "${key}=\"${value}\""])} ${join(" ", [for key, value in var.general : "${key}=\"${value}\""])}'"
  }

}

resource "aws_eip" "windows_ip" {
  count = length(var.windows_servers)
  instance = aws_instance.windows_server[count.index].id
}
