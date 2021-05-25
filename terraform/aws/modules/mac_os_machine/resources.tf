data "aws_ami" "macos" {
  count       = var.config.mac_os_machine == "1" ? 1 : 0
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn-ec2-macos-10.15*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

module "dedicated-host" {
  source            = "DanielRDias/dedicated-host/aws"
  version           = "0.3.0"
  instance_type     = "mac1.metal"
  availability_zone = "eu-west-1a"
  cf_stack_name     = "mac-stack"

    tags = {
    Name = "Terraform Mac"
  }
}

resource "aws_instance" "mac_os_machine" {
  count                  = var.config.mac_os_machine == "1" ? 1 : 0  
  ami                    = data.aws_ami.macos[count.index].id
  instance_type          = var.config.mac_os_instance_type
  key_name               = var.config.key_name
  subnet_id              = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  host_id                = module.dedicated-host.dedicated_host_id
  private_ip             = var.config.mac_os_private_ip
  tags = {
    Name = "ar-macos-${var.config.range_name}-${var.config.key_name}"
  }


  provisioner "remote-exec" {
    inline = ["echo booted"]
  
    connection {
      type        = "ssh"
      user        = "ec2-user"
      host        = aws_instance.mac_os_machine[count.index].public_ip
      private_key = file(var.config.private_key_path)
      timeout    = "60m"
    }
  }

  provisioner "local-exec" {
    working_dir = "../../ansible/"
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -u ec2-user --private-key ${var.config.private_key_path} -i '${aws_instance.mac_os_machine[count.index].public_ip},' playbooks/mac_os_machine.yml -e 'splunk_indexer_ip=${var.config.splunk_server_private_ip} splunk_uf_url=${var.config.splunk_uf_mac_url} custom_osquery_conf=${var.config.macos_custom_config_file}'"
  }


}

output "dedicated_host_id" {
  description = "Dedicated Host ID"
  value = module.dedicated-host.dedicated_host_id
}

resource "aws_eip" "macos_ip" {
  count    = var.config.mac_os_machine == "1" && var.config.use_elastic_ips == "1" ? 1 : 0
  instance = aws_instance.mac_os_machine[0].id

}

