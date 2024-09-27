
data "aws_ami" "latest-kali-linux" {
  count       = var.kali_server.kali_server == "1" ? 1 : 0
  most_recent = true
  owners      = ["679593333241"] # owned by AWS marketplace

  filter {
      name   = "name"
      values = ["kali-last-snapshot-amd64-2023*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "kali_machine" {
  count                  = var.kali_server.kali_server == "1" ? 1 : 0
  ami                    = data.aws_ami.latest-kali-linux[count.index].id
  instance_type          = "t3.large"
  key_name               = var.general.key_name
  subnet_id              = var.ec2_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip             = "10.0.1.30"
  associate_public_ip_address = true
  
  tags = {
    Name = "ar-kali-${var.general.key_name}-${var.general.attack_range_name}"
  }

  provisioner "remote-exec" {
    inline = ["echo booted"]

    connection {
      type        = "ssh"
      user        = "kali"
      host        = self.public_ip
      private_key = file(var.aws.private_key_path)
    }
  }

}

resource "aws_eip" "kali_ip" {
  count    = (var.kali_server.kali_server == "1") && (var.aws.use_elastic_ips == "1") ? 1 : 0
  instance = aws_instance.kali_machine[0].id
}
