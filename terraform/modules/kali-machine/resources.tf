
# standup splunk server
resource "aws_instance" "kali-machine" {
  count         = var.kali-machine ? 1 : 0
  ami           = var.kali_ami
  instance_type = "t2.medium"
  key_name = var.key_name
  subnet_id = var.vpc_subnet0_id
  vpc_security_group_ids = [var.vpc_security_group_ids]

  tags = {
    Name = "attack-range-kali-machine"
  }
}

resource "aws_eip" "kali_ip" {
  count         = var.kali-machine ? 1 : 0
  instance = aws_instance.kali-machine[0].id
}
