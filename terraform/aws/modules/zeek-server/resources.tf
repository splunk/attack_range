resource "aws_security_group" "zeek_server" {
  count       = var.zeek_server ? 1 : 0
  name        = "ar-${var.server_name}-${var.attack_range_id}-sg"
  description = "Security group allowing all ingress and egress traffic"
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

resource "aws_instance" "zeek_sensor" {
  count                  = var.zeek_server ? 1 : 0
  ami                    = var.ami_id
  instance_type          = "m5.2xlarge"
  key_name               = var.key_name
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.zeek_server[0].id]
  private_ip             = var.private_ip
  metadata_options {
    http_tokens = "required"
  }

  tags = {
    Name = "ar-${var.server_name}-${var.attack_range_id}"
  }

  root_block_device {
    volume_type           = var.root_volume_type
    volume_size           = var.root_volume_size
    delete_on_termination = var.root_volume_delete_on_termination
    encrypted             = var.root_volume_encrypted
  }
}

resource "aws_ec2_traffic_mirror_target" "zeek_target" {
  count                = var.zeek_server ? 1 : 0
  description          = "VPC Tap for Zeek"
  network_interface_id = aws_instance.zeek_sensor[0].primary_network_interface_id
}

resource "aws_ec2_traffic_mirror_filter" "zeek_filter" {
  count       = var.zeek_server ? 1 : 0
  description = "Zeek Mirror Filter - Allow All"
}

resource "aws_ec2_traffic_mirror_filter_rule" "zeek_outbound" {
  count                    = var.zeek_server ? 1 : 0
  description              = "Zeek Outbound Rule"
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.zeek_filter[0].id
  destination_cidr_block   = "0.0.0.0/0"
  source_cidr_block        = "0.0.0.0/0"
  rule_number              = 1
  rule_action              = "accept"
  traffic_direction        = "egress"
}

resource "aws_ec2_traffic_mirror_filter_rule" "zeek_inbound" {
  count                    = var.zeek_server ? 1 : 0
  description              = "Zeek Inbound Rule"
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.zeek_filter[0].id
  destination_cidr_block   = "0.0.0.0/0"
  source_cidr_block        = "0.0.0.0/0"
  rule_number              = 1
  rule_action              = "accept"
  traffic_direction        = "ingress"
}
