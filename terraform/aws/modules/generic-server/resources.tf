
resource "aws_security_group" "this" {
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

resource "aws_instance" "this" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name != null ? var.key_name : null
  subnet_id              = var.subnet_id
  private_ip             = var.private_ip
  vpc_security_group_ids = [aws_security_group.this.id]
  user_data              = var.user_data
  metadata_options {
    http_tokens = "required"
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

output "instance_id" {
  description = "IDs of the created instance."
  value       = aws_instance.this.id
}

output "instance" {
  description = "The EC2 instance object."
  value       = aws_instance.this
}

resource "aws_ec2_traffic_mirror_session" "zeek_session" {
  for_each = var.zeek_monitor ? { zeek = true } : {}

  description              = "Zeek Mirror Session for ${var.server_name}"
  depends_on               = [aws_instance.this]
  traffic_mirror_filter_id = var.zeek_traffic_mirror_filter_id
  traffic_mirror_target_id = var.zeek_traffic_mirror_target_id
  network_interface_id     = aws_instance.this.primary_network_interface_id
  session_number           = var.zeek_session_number
}
