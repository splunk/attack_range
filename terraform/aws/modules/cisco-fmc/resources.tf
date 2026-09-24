locals {
  day0 = {
    AdminPassword = var.admin_password
    Hostname      = var.hostname
  }
}

resource "aws_security_group" "this" {
  name        = "ar-${var.server_name}-${var.attack_range_id}-sg"
  description = "Security group for Cisco FMCv"
  vpc_id      = var.vpc_id

  ingress {
    description = "Allow all inbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ar-${var.server_name}-${var.attack_range_id}-sg"
  }
}

resource "aws_network_interface" "mgmt" {
  subnet_id         = var.subnet_id
  private_ips       = [var.private_ip]
  security_groups   = [aws_security_group.this.id]
  source_dest_check = true

  tags = {
    Name = "ar-${var.server_name}-mgmt-${var.attack_range_id}"
  }
}

resource "aws_instance" "this" {
  ami           = var.ami_id
  instance_type = var.instance_type
  key_name      = var.key_name
  user_data     = "#FMC\n${jsonencode(local.day0)}"

  network_interface {
    network_interface_id = aws_network_interface.mgmt.id
    device_index         = 0
  }

  root_block_device {
    volume_type           = var.root_volume_type
    volume_size           = var.root_volume_size
    delete_on_termination = var.root_volume_delete_on_termination
    encrypted             = var.root_volume_encrypted
  }

  tags = {
    Name = "ar-${var.server_name}-${var.attack_range_id}"
  }
}
