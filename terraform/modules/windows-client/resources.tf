
data "aws_ami" "windows-client-ami" {
  count = var.config.windows_client == "1" ? 1 : 0
  owners       = ["self"]

  filter {
    name   = "name"
    values = [var.config.windows_client_os]
  }

  most_recent = true
}


resource "aws_instance" "windows_client" {
  count         = var.config.windows_client == "1" ? 1 : 0
  ami           = data.aws_ami.windows-client-ami[count.index].id
  instance_type = "t2.2xlarge"
  key_name = var.config.key_name
  subnet_id = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip = var.config.windows_client_private_ip
  depends_on = [var.windows_domain_controller_instance]
  tags = {
    Name = "attack-range-windows-client"
  }

  provisioner "remote-exec" {
    inline = [
      "net user ${var.config.win_username} /active:yes",
      "net user ${var.config.win_username} ${var.config.win_password}"
      ]

    connection {
      type     = "winrm"
      user     = "admin"
      password = "admin"
      host     = aws_instance.windows_client[count.index].public_ip
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
      user     = var.config.win_username
      password = var.config.win_password
      host     = aws_instance.windows_client[count.index].public_ip
      port     = 5985
      insecure = true
      https    = false
      timeout  = "7m"
    }
  }

  provisioner "local-exec" {
    working_dir = "../ansible"
    command = "ansible-playbook -i '${aws_instance.windows_client[count.index].public_ip},' playbooks/windows_workstation.yml --extra-vars 'splunk_indexer_ip=${var.config.splunk_server_private_ip} ansible_user=${var.config.win_username} ansible_password=${var.config.win_password} win_password=${var.config.win_password} splunk_uf_win_url=${var.config.splunk_uf_win_url} nxlog_url=${var.config.nxlog_url} win_sysmon_url=${var.config.win_sysmon_url} win_sysmon_template=${var.config.win_sysmon_template} splunk_admin_password=${var.config.splunk_admin_password} windows_domain_controller_private_ip=${var.config.windows_domain_controller_private_ip} windows_server_join_domain=${var.config.windows_client_join_domain} splunk_stream_app=${var.config.splunk_stream_app} s3_bucket_url=${var.config.s3_bucket_url}'"
  }

}

resource "aws_eip" "windows_client_ip" {
  count         = var.config.windows_client == "1" ? 1 : 0
  instance = aws_instance.windows_client[0].id
}
