
resource "aws_security_group" "default" {
  name   = "ar_sg_router_${var.attack_range_id}"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ip_whitelist]
  }

  ingress {
    from_port   = 51820
    to_port     = 51820
    protocol    = "udp"
    cidr_blocks = [var.ip_whitelist]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "router" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  subnet_id              = var.subnet_id
  private_ip             = var.private_ip
  vpc_security_group_ids = [aws_security_group.default.id]
  metadata_options {
    http_tokens = "required"
  }

  associate_public_ip_address = true

  root_block_device {
    volume_type           = "gp3"
    volume_size           = "30"
    delete_on_termination = "true"
    encrypted             = "true"
  }

  tags = {
    Name = "ar-router-${var.attack_range_id}"
  }
}
