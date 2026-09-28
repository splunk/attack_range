locals {
  manage_locally = var.fmc_ip == null || var.fmc_ip == ""
  day0 = merge(
    {
      AdminPassword = var.admin_password
      Hostname      = var.hostname
      FirewallMode  = "Routed"
      ManageLocally = local.manage_locally ? "Yes" : "No"
    },
    local.manage_locally ? {} : {
      FmcIp     = var.fmc_ip
      FmcRegKey = var.reg_key
      FmcNatId  = var.nat_id
    }
  )
}

resource "aws_security_group" "this" {
  name        = "ar-${var.server_name}-${var.attack_range_id}-sg"
  description = "Security group for Cisco FTDv"
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
  subnet_id         = var.mgmt_subnet_id
  private_ips       = [var.mgmt_private_ip]
  security_groups   = [aws_security_group.this.id]
  source_dest_check = false

  tags = {
    Name = "ar-${var.server_name}-mgmt-${var.attack_range_id}"
  }
}

resource "aws_network_interface" "diag" {
  subnet_id         = var.diag_subnet_id
  private_ips       = [var.diag_private_ip]
  security_groups   = [aws_security_group.this.id]
  source_dest_check = false

  tags = {
    Name = "ar-${var.server_name}-diag-${var.attack_range_id}"
  }
}

resource "aws_network_interface" "outside" {
  subnet_id         = var.outside_subnet_id
  private_ips       = [var.outside_private_ip]
  security_groups   = [aws_security_group.this.id]
  source_dest_check = false

  tags = {
    Name = "ar-${var.server_name}-outside-${var.attack_range_id}"
  }
}

resource "aws_network_interface" "inside" {
  subnet_id         = var.inside_subnet_id
  private_ips       = [var.inside_private_ip]
  security_groups   = [aws_security_group.this.id]
  source_dest_check = false

  tags = {
    Name = "ar-${var.server_name}-inside-${var.attack_range_id}"
  }
}

resource "aws_instance" "this" {
  ami           = var.ami_id
  instance_type = var.instance_type
  key_name      = var.key_name
  user_data     = "#Sensor\n${jsonencode(local.day0)}"

  # Device order matches Cisco's AWS FTDv module: mgmt, diag, outside, inside.
  network_interface {
    network_interface_id = aws_network_interface.mgmt.id
    device_index         = 0
  }

  network_interface {
    network_interface_id = aws_network_interface.diag.id
    device_index         = 1
  }

  network_interface {
    network_interface_id = aws_network_interface.outside.id
    device_index         = 2
  }

  network_interface {
    network_interface_id = aws_network_interface.inside.id
    device_index         = 3
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
