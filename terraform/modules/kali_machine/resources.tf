
data "aws_ami" "latest-kali-linux" {
most_recent = true
owners = ["679593333241"] # Canonical

  filter {
      name   = "name"
      values = ["Kali Linux 2018.1-*"]
  }

  filter {
      name   = "virtualization-type"
      values = ["hvm"]
  }
}

# standup splunk server
resource "aws_instance" "kali_machine" {
  count         = var.kali_machine ? 1 : 0
  ami           = "${data.aws_ami.latest-kali-linux.id}"
  instance_type = "t2.medium"
  key_name = var.key_name
  subnet_id = var.vpc_subnet_id
  vpc_security_group_ids = [var.vpc_security_group_ids]
  private_ip = var.kali_machine_private_ip
  tags = {
    Name = "attack-range-kali_machine"
  }
}

resource "aws_eip" "kali_ip" {
  count         = var.kali_machine ? 1 : 0
  instance = aws_instance.kali_machine[0].id
}
