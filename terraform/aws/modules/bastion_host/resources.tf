resource "aws_security_group" "main" {
  name   = "${var.general.key_name}_${var.general.attack_range_name}-bastion-host-sg"
  vpc_id = var.aws.vpc_id
}

resource "aws_security_group_rule" "allow_inbound_ssh" {
  type              = "ingress"
  from_port         = "22"
  to_port           = "22"
  protocol          = "tcp"
  cidr_blocks       = split(",", var.general.ip_whitelist)
  security_group_id = aws_security_group.main.id
}

# allow outgoing traffic
resource "aws_security_group_rule" "allow_all_outbound" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.main.id
}

data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm*"]
  }
}

resource "aws_instance" "bastion_host" {
  ami                         = data.aws_ami.amazon_linux_2.id
  instance_type               = "t3.micro"
  key_name                    = var.general.key_name
  subnet_id                   = var.ec2_subnet_id
  private_ip                  = var.aws.bastion_host_ip
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.main.id]
  iam_instance_profile        = var.instance_profile_name
  tags = {
    Name = "ar-bastion-${var.general.key_name}-${var.general.attack_range_name}"
  }
}

resource "aws_eip" "bastion_ip" {
  count    = (var.aws.use_elastic_ips == "1") ? 1 : 0
  instance = aws_instance.bastion_host.id
}
